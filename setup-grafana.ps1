$ErrorActionPreference = "Stop"

# ============================================================
# AI IT Operations - Complete Grafana Setup
#
# Grafana 12.1.x
# Prometheus 3.x
#
# Creates/repairs:
#   - Prometheus datasource
#   - AI IT Operations folder
#   - AI IT Operations dashboard
#   - 6 Grafana-managed alert rules
#
# Safe to run repeatedly.
# ============================================================

$GrafanaUrl = "http://localhost:3000"
$PrometheusUrlFromGrafana = "http://prometheus:9090"

# ------------------------------------------------------------
# TOKEN
# ------------------------------------------------------------

if ([string]::IsNullOrWhiteSpace($env:GRAFANA_TOKEN)) {
    Write-Host ""
    Write-Host "ERROR: GRAFANA_TOKEN is not set." -ForegroundColor Red
    Write-Host ""
    Write-Host 'Run this first:' -ForegroundColor Yellow
    Write-Host '$env:GRAFANA_TOKEN = "YOUR_NEW_GRAFANA_TOKEN"' -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

$Headers = @{
    Authorization  = "Bearer $env:GRAFANA_TOKEN"
    "Content-Type" = "application/json"
}

# ------------------------------------------------------------
# GRAFANA API HELPER
# ------------------------------------------------------------

function Invoke-Grafana {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Uri,

        [Parameter(Mandatory=$false)]
        [ValidateSet("GET","POST","PUT","DELETE")]
        [string]$Method = "GET",

        [Parameter(Mandatory=$false)]
        $Body
    )

    $params = @{
        Uri     = $Uri
        Method  = $Method
        Headers = $Headers
    }

    if ($null -ne $Body) {
        $params.Body = $Body | ConvertTo-Json -Depth 50
    }

    try {
        return Invoke-RestMethod @params
    }
    catch {
        $message = $_.Exception.Message

        if ($_.ErrorDetails.Message) {
            $message = $_.ErrorDetails.Message
        }

        throw "Grafana API $Method $Uri failed: $message"
    }
}

# ------------------------------------------------------------
# 1. GRAFANA HEALTH
# ------------------------------------------------------------

function Test-Grafana {

    Write-Host ""
    Write-Host "[1/5] Checking Grafana..." -ForegroundColor Cyan

    $health = Invoke-RestMethod `
        -Uri "$GrafanaUrl/api/health" `
        -Method GET

    if ($health.database -ne "ok") {
        throw "Grafana health check failed."
    }

    Write-Host "Grafana is healthy." -ForegroundColor Green
}

# ------------------------------------------------------------
# 2. PROMETHEUS DATASOURCE
# ------------------------------------------------------------

function Get-OrCreate-PrometheusDatasource {

    Write-Host ""
    Write-Host "[2/5] Checking Prometheus datasource..." -ForegroundColor Cyan

    $sources = @(Invoke-Grafana `
        -Uri "$GrafanaUrl/api/datasources" `
        -Method GET)

    $prom = $sources |
        Where-Object {
            $_.type -eq "prometheus" -or
            $_.name -eq "Prometheus"
        } |
        Select-Object -First 1

    # --------------------------------------------------------
    # CREATE DATASOURCE IF MISSING
    # --------------------------------------------------------

    if ($null -eq $prom) {

        Write-Host "Prometheus datasource not found." -ForegroundColor Yellow
        Write-Host "Creating Prometheus datasource..." -ForegroundColor Yellow

        $body = @{
            name      = "Prometheus"
            type      = "prometheus"
            access    = "proxy"
            url       = $PrometheusUrlFromGrafana
            isDefault = $true

            jsonData = @{
                httpMethod   = "POST"
                manageAlerts = $false
            }
        }

        $created = Invoke-Grafana `
            -Uri "$GrafanaUrl/api/datasources" `
            -Method POST `
            -Body $body

        $script:DataSourceUid = $created.datasource.uid

        if ([string]::IsNullOrWhiteSpace($script:DataSourceUid)) {
            throw "Prometheus datasource was created but Grafana returned no UID."
        }

        Write-Host "Prometheus datasource created." -ForegroundColor Green
        Write-Host "Datasource UID: $script:DataSourceUid" -ForegroundColor Green

        return
    }

    # --------------------------------------------------------
    # EXISTING DATASOURCE
    # --------------------------------------------------------

    $script:DataSourceUid = $prom.uid

    if ([string]::IsNullOrWhiteSpace($script:DataSourceUid)) {
        throw "Prometheus datasource exists but has no UID."
    }

    Write-Host "Found Prometheus datasource." -ForegroundColor Green
    Write-Host "Name: $($prom.name)" -ForegroundColor DarkGray
    Write-Host "UID:  $script:DataSourceUid" -ForegroundColor Green
    Write-Host "URL:  $($prom.url)" -ForegroundColor DarkGray

    # --------------------------------------------------------
    # REPAIR DOCKER URL
    # --------------------------------------------------------

    if ($prom.url -ne $PrometheusUrlFromGrafana) {

        Write-Host ""
        Write-Host "Datasource URL is incorrect for Docker Compose." -ForegroundColor Yellow
        Write-Host "Changing URL to $PrometheusUrlFromGrafana" -ForegroundColor Yellow

        $jsonData = $prom.jsonData

        if ($null -eq $jsonData) {
            $jsonData = @{
                httpMethod   = "POST"
                manageAlerts = $false
            }
        }

        $update = @{
            name      = $prom.name
            type      = "prometheus"
            access    = "proxy"
            url       = $PrometheusUrlFromGrafana
            isDefault = $true
            jsonData  = $jsonData
        }

        Invoke-Grafana `
            -Uri "$GrafanaUrl/api/datasources/uid/$($prom.uid)" `
            -Method PUT `
            -Body $update | Out-Null

        Write-Host "Datasource URL repaired." -ForegroundColor Green
    }

    # --------------------------------------------------------
    # DATASOURCE HEALTH
    # --------------------------------------------------------

    try {

        $health = Invoke-Grafana `
            -Uri "$GrafanaUrl/api/datasources/uid/$script:DataSourceUid/health" `
            -Method GET

        Write-Host ""
        Write-Host "Prometheus datasource health: $($health.status)" `
            -ForegroundColor Green

    }
    catch {

        Write-Warning "Prometheus datasource health check failed."
        Write-Warning $_
    }
}

# ------------------------------------------------------------
# 3. FOLDER
# ------------------------------------------------------------

function Get-OrCreate-Folder {

    Write-Host ""
    Write-Host "[3/5] Checking Grafana folder..." -ForegroundColor Cyan

    $folderName = "AI IT Operations"
    $desiredFolderUid = "ai-it-operations"

    # --------------------------------------------------------
    # TRY UID
    # --------------------------------------------------------

    try {

        $folder = Invoke-Grafana `
            -Uri "$GrafanaUrl/api/folders/$desiredFolderUid" `
            -Method GET

        $script:FolderUid = $folder.uid

        Write-Host "Folder already exists." -ForegroundColor Green
        Write-Host "Name: $($folder.title)" -ForegroundColor DarkGray
        Write-Host "UID:  $script:FolderUid" -ForegroundColor Green

        return
    }
    catch {
        # Continue.
    }

    # --------------------------------------------------------
    # TRY NAME
    # --------------------------------------------------------

    try {

        $encodedName = [uri]::EscapeDataString($folderName)

        $folder = Invoke-Grafana `
            -Uri "$GrafanaUrl/api/folders/name/$encodedName" `
            -Method GET

        $script:FolderUid = $folder.uid

        Write-Host "Folder found by name." -ForegroundColor Green
        Write-Host "UID: $script:FolderUid" -ForegroundColor Green

        return
    }
    catch {
        # Continue.
    }

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    Write-Host "Creating folder '$folderName'..." -ForegroundColor Yellow

    $body = @{
        uid   = $desiredFolderUid
        title = $folderName
    }

    $created = Invoke-Grafana `
        -Uri "$GrafanaUrl/api/folders" `
        -Method POST `
        -Body $body

    $script:FolderUid = $created.uid

    Write-Host "Folder created." -ForegroundColor Green
    Write-Host "UID: $script:FolderUid" -ForegroundColor Green
}

# ------------------------------------------------------------
# PROMETHEUS TARGET
# ------------------------------------------------------------

function New-Target {

    param(
        [string]$RefId,
        [string]$Expr,
        [bool]$Instant = $false,
        [bool]$Range = $true
    )

    return @{
        refId       = $RefId

        datasource = @{
            type = "prometheus"
            uid  = $script:DataSourceUid
        }

        editorMode = "code"
        expr       = $Expr
        instant    = $Instant
        range      = $Range
        format     = "time_series"
    }
}

# ------------------------------------------------------------
# STAT PANEL
# ------------------------------------------------------------

function New-StatPanel {

    param(
        [int]$Id,
        [string]$Title,
        [int]$X,
        [int]$Y,
        [int]$W,
        [int]$H,
        [string]$Expr,
        [string]$Unit = "percent"
    )

    return @{
        id = $Id
        type = "stat"
        title = $Title

        gridPos = @{
            h = $H
            w = $W
            x = $X
            y = $Y
        }

        datasource = @{
            type = "prometheus"
            uid  = $script:DataSourceUid
        }

        targets = @(
            (
                New-Target `
                    -RefId "A" `
                    -Expr $Expr `
                    -Instant $true `
                    -Range $false
            )
        )

        fieldConfig = @{
            defaults = @{
                unit = $Unit

                min = 0

                max = 100

                thresholds = @{
                    mode = "absolute"

                    steps = @(
                        @{
                            color = "green"
                            value = $null
                        }
                        @{
                            color = "yellow"
                            value = 70
                        }
                        @{
                            color = "red"
                            value = 90
                        }
                    )
                }
            }

            overrides = @()
        }

        options = @{
            reduceOptions = @{
                values = $false
                calcs = @("lastNotNull")
                fields = ""
            }

            orientation = "auto"
            textMode = "auto"
            colorMode = "value"
            graphMode = "none"
            justifyMode = "auto"
        }
    }
}

# ------------------------------------------------------------
# TIMESERIES PANEL
# ------------------------------------------------------------

function New-TimeSeriesPanel {

    param(
        [int]$Id,
        [string]$Title,
        [int]$X,
        [int]$Y,
        [int]$W,
        [int]$H,
        [string]$Expr,
        [string]$Unit = "short"
    )

    return @{
        id = $Id
        type = "timeseries"
        title = $Title

        gridPos = @{
            h = $H
            w = $W
            x = $X
            y = $Y
        }

        datasource = @{
            type = "prometheus"
            uid  = $script:DataSourceUid
        }

        targets = @(
            (
                New-Target `
                    -RefId "A" `
                    -Expr $Expr `
                    -Instant $false `
                    -Range $true
            )
        )

        fieldConfig = @{
            defaults = @{
                unit = $Unit
            }

            overrides = @()
        }

        options = @{
            tooltip = @{
                mode = "multi"
                sort = "desc"
            }

            legend = @{
                displayMode = "list"
                placement = "bottom"
            }
        }
    }
}

# ------------------------------------------------------------
# 4. DASHBOARD
# ------------------------------------------------------------

function New-Dashboard {

    Write-Host ""
    Write-Host "[4/5] Creating/updating dashboard..." -ForegroundColor Cyan

    $dashboard = @{
        uid = "ai-it-ops-dashboard"

        title = "AI IT Operations"

        tags = @(
            "ai-it-ops"
            "infrastructure"
            "prometheus"
        )

        timezone = "browser"

        schemaVersion = 39

        version = 0

        refresh = "10s"

        time = @{
            from = "now-30m"
            to   = "now"
        }

        timepicker = @{
            refresh_intervals = @(
                "5s"
                "10s"
                "30s"
                "1m"
                "5m"
                "15m"
                "30m"
                "1h"
            )
        }

        panels = @(

            # ------------------------------------------------
            # TOP ROW
            # ------------------------------------------------

            (
                New-StatPanel `
                    -Id 1 `
                    -Title "CPU Utilization" `
                    -X 0 `
                    -Y 0 `
                    -W 8 `
                    -H 5 `
                    -Expr "itops_cpu_percent"
            )

            (
                New-StatPanel `
                    -Id 2 `
                    -Title "RAM Utilization" `
                    -X 8 `
                    -Y 0 `
                    -W 8 `
                    -H 5 `
                    -Expr "itops_ram_percent"
            )

            (
                New-StatPanel `
                    -Id 3 `
                    -Title "Disk Utilization" `
                    -X 16 `
                    -Y 0 `
                    -W 8 `
                    -H 5 `
                    -Expr "itops_disk_percent"
            )

            # ------------------------------------------------
            # REQUESTS + LATENCY
            # ------------------------------------------------

            (
                New-TimeSeriesPanel `
                    -Id 4 `
                    -Title "Telemetry Request Rate" `
                    -X 0 `
                    -Y 5 `
                    -W 12 `
                    -H 8 `
                    -Expr "rate(itops_telemetry_requests_total[5m])" `
                    -Unit "short"
            )

            (
                New-TimeSeriesPanel `
                    -Id 5 `
                    -Title "95th Percentile Request Latency" `
                    -X 12 `
                    -Y 5 `
                    -W 12 `
                    -H 8 `
                    -Expr "histogram_quantile(0.95, sum(rate(itops_request_latency_seconds_bucket[5m])) by (le))" `
                    -Unit "s"
            )

            # ------------------------------------------------
            # INFRASTRUCTURE
            # ------------------------------------------------

            (
                New-TimeSeriesPanel `
                    -Id 6 `
                    -Title "Infrastructure Utilization" `
                    -X 0 `
                    -Y 13 `
                    -W 24 `
                    -H 8 `
                    -Expr 'avg({__name__=~"itops_(cpu|ram|disk)_percent"})' `
                    -Unit "percent"
            )

            # ------------------------------------------------
            # BOTTOM ROW
            # ------------------------------------------------

            (
                New-StatPanel `
                    -Id 7 `
                    -Title "Incidents Created" `
                    -X 0 `
                    -Y 21 `
                    -W 8 `
                    -H 5 `
                    -Expr "sum(increase(itops_incidents_created_total[30m]))" `
                    -Unit "short"
            )

            (
                New-StatPanel `
                    -Id 8 `
                    -Title "Anomalies Detected" `
                    -X 8 `
                    -Y 21 `
                    -W 8 `
                    -H 5 `
                    -Expr "sum(increase(itops_anomalies_detected_total[30m]))" `
                    -Unit "short"
            )

            (
                New-StatPanel `
                    -Id 9 `
                    -Title "Current Infrastructure Status" `
                    -X 16 `
                    -Y 21 `
                    -W 8 `
                    -H 5 `
                    -Expr 'max({__name__=~"itops_(cpu|ram|disk)_percent"})' `
                    -Unit "percent"
            )
        )
    }

    $body = @{
        dashboard = $dashboard

        folderUid = $script:FolderUid

        overwrite = $true

        message = "AI IT Operations automated deployment"
    }

    $result = Invoke-Grafana `
        -Uri "$GrafanaUrl/api/dashboards/db" `
        -Method POST `
        -Body $body

    Write-Host ""
    Write-Host "Dashboard deployed successfully." -ForegroundColor Green
    Write-Host "Dashboard UID: $($result.uid)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Open:" -ForegroundColor Cyan
    Write-Host "$GrafanaUrl/d/$($result.uid)/ai-it-operations" -ForegroundColor Yellow
}

# ------------------------------------------------------------
# ALERT DATA
# ------------------------------------------------------------

function New-AlertData {

    param(
        [string]$Expression,
        [double]$Threshold
    )

    return @(

        # ----------------------------------------------------
        # PROMETHEUS QUERY
        # ----------------------------------------------------

        @{
            refId = "A"

            queryType = ""

            datasourceUid = $script:DataSourceUid

            relativeTimeRange = @{
                from = 600
                to   = 0
            }

            model = @{
                datasource = @{
                    type = "prometheus"
                    uid  = $script:DataSourceUid
                }

                editorMode = "code"

                expr = $Expression

                instant = $true

                intervalMs = 1000

                maxDataPoints = 43200

                range = $false

                refId = "A"
            }
        }

        # ----------------------------------------------------
        # THRESHOLD EXPRESSION
        # ----------------------------------------------------

        @{
            refId = "C"

            queryType = ""

            datasourceUid = "__expr__"

            relativeTimeRange = @{
                from = 0
                to   = 0
            }

            model = @{

                conditions = @(
                    @{
                        evaluator = @{
                            params = @($Threshold)
                            type = "gt"
                        }

                        operator = @{
                            type = "and"
                        }

                        query = @{
                            params = @("A")
                        }

                        reducer = @{
                            params = @()
                            type = "last"
                        }

                        type = "query"
                    }
                )

                datasource = @{
                    type = "__expr__"
                    uid = "__expr__"
                }

                expression = "A"

                refId = "C"

                type = "threshold"
            }
        }
    )
}

# ------------------------------------------------------------
# ALERT RULE UPSERT
# ------------------------------------------------------------

function Upsert-AlertRule {

    param(
        [string]$Title,
        [string]$Uid,
        [string]$Expression,
        [double]$Threshold,
        [string]$Summary,
        [string]$Description
    )

    Write-Host ""
    Write-Host "Creating/updating: $Title" -ForegroundColor Cyan

    $body = @{
        title = $Title

        uid = $Uid

        ruleGroup = "AI IT Operations"

        folderUID = $script:FolderUid

        interval = "30s"

        noDataState = "NoData"

        execErrState = "Error"

        for = "0s"

        condition = "C"

        orgId = 1

        annotations = @{
            summary = $Summary
            description = $Description
        }

        labels = @{
            severity = "critical"
            team = "infrastructure"
        }

        data = New-AlertData `
            -Expression $Expression `
            -Threshold $Threshold

        isPaused = $false
    }

    # --------------------------------------------------------
    # TRY UPDATE FIRST
    # --------------------------------------------------------

    try {

        Invoke-Grafana `
            -Uri "$GrafanaUrl/api/v1/provisioning/alert-rules/$Uid" `
            -Method PUT `
            -Body $body | Out-Null

        Write-Host "UPDATED: $Title" -ForegroundColor Green

        return
    }
    catch {
        # Rule doesn't exist.
    }

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    try {

        Invoke-Grafana `
            -Uri "$GrafanaUrl/api/v1/provisioning/alert-rules" `
            -Method POST `
            -Body $body | Out-Null

        Write-Host "CREATED: $Title" -ForegroundColor Green
    }
    catch {

        throw "FAILED: $Title`n$($_.Exception.Message)"
    }
}

# ------------------------------------------------------------
# REMOVE OLD DUPLICATE RULES
# ------------------------------------------------------------

function Remove-OldDuplicateRules {

    Write-Host ""
    Write-Host "Checking for old duplicate alert rules..." `
        -ForegroundColor DarkGray

    $desiredTitles = @(
        "High CPU Utilization"
        "High RAM Utilization"
        "Critical Disk Utilization"
        "High Request Latency"
        "Incident Created"
        "Anomalies Detected"
    )

    $desiredUids = @(
        "high_cpu_utilization"
        "high_ram_utilization"
        "critical_disk_utilization"
        "high_request_latency"
        "incident_created"
        "anomalies_detected"
    )

    $rules = @(Invoke-Grafana `
        -Uri "$GrafanaUrl/api/v1/provisioning/alert-rules" `
        -Method GET)

    foreach ($rule in $rules) {

        if ($desiredTitles -contains $rule.title) {

            if ($desiredUids -notcontains $rule.uid) {

                Write-Host ""
                Write-Host "Deleting old duplicate:" `
                    -ForegroundColor Yellow

                Write-Host "$($rule.title) [$($rule.uid)]" `
                    -ForegroundColor Yellow

                try {

                    Invoke-Grafana `
                        -Uri "$GrafanaUrl/api/v1/provisioning/alert-rules/$($rule.uid)" `
                        -Method DELETE | Out-Null

                    Write-Host "Deleted." -ForegroundColor Green
                }
                catch {

                    Write-Warning `
                        "Could not delete old rule $($rule.uid)"
                }
            }
        }
    }
}

# ------------------------------------------------------------
# 5. ALERT RULES
# ------------------------------------------------------------

function New-AlertRules {

    Write-Host ""
    Write-Host "[5/5] Creating/updating alert rules..." `
        -ForegroundColor Cyan

    Remove-OldDuplicateRules

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    Upsert-AlertRule `
        -Title "High CPU Utilization" `
        -Uid "high_cpu_utilization" `
        -Expression "itops_cpu_percent" `
        -Threshold 90 `
        -Summary "CPU utilization is critically high" `
        -Description "CPU utilization is above 90%."

    # --------------------------------------------------------
    # RAM
    # --------------------------------------------------------

    Upsert-AlertRule `
        -Title "High RAM Utilization" `
        -Uid "high_ram_utilization" `
        -Expression "itops_ram_percent" `
        -Threshold 90 `
        -Summary "RAM utilization is critically high" `
        -Description "RAM utilization is above 90%."

    # --------------------------------------------------------
    # DISK
    # --------------------------------------------------------

    Upsert-AlertRule `
        -Title "Critical Disk Utilization" `
        -Uid "critical_disk_utilization" `
        -Expression "itops_disk_percent" `
        -Threshold 90 `
        -Summary "Disk utilization is critically high" `
        -Description "Disk utilization is above 90%."

    # --------------------------------------------------------
    # LATENCY
    # --------------------------------------------------------

    Upsert-AlertRule `
        -Title "High Request Latency" `
        -Uid "high_request_latency" `
        -Expression "histogram_quantile(0.95, sum(rate(itops_request_latency_seconds_bucket[5m])) by (le))" `
        -Threshold 1 `
        -Summary "Request latency is critically high" `
        -Description "The 95th percentile request latency is above 1 second."

    # --------------------------------------------------------
    # INCIDENT
    # --------------------------------------------------------

    Upsert-AlertRule `
        -Title "Incident Created" `
        -Uid "incident_created" `
        -Expression "sum(increase(itops_incidents_created_total[5m]))" `
        -Threshold 0 `
        -Summary "A new IT incident has been detected" `
        -Description "At least one new IT incident was created during the last 5 minutes."

    # --------------------------------------------------------
    # ANOMALY
    # --------------------------------------------------------

    Upsert-AlertRule `
        -Title "Anomalies Detected" `
        -Uid "anomalies_detected" `
        -Expression "sum(increase(itops_anomalies_detected_total[5m]))" `
        -Threshold 0 `
        -Summary "IT anomalies have been detected" `
        -Description "One or more anomalies were detected during the last 5 minutes."
}

# ============================================================
# EXECUTION
# ============================================================

Test-Grafana

Get-OrCreate-PrometheusDatasource

Get-OrCreate-Folder

New-Dashboard

New-AlertRules

# ============================================================
# FINISHED
# ============================================================

Write-Host ""
Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host "AI IT Operations Grafana setup completed." `
    -ForegroundColor Green

Write-Host ""
Write-Host "Folder UID:     $script:FolderUid"
Write-Host "Datasource UID: $script:DataSourceUid"
Write-Host "Dashboard UID:  ai-it-ops-dashboard"

Write-Host ""
Write-Host "Dashboard:" -ForegroundColor Cyan
Write-Host "$GrafanaUrl/d/ai-it-ops-dashboard/ai-it-operations" `
    -ForegroundColor Yellow

Write-Host ""
Write-Host "============================================================" `
    -ForegroundColor Cyan