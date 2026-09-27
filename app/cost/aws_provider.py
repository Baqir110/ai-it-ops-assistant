"""AWS cost analysis provider.

Fetches actual AWS pricing data and resource utilization to generate
cost optimization recommendations. Uses boto3 for AWS API access.

This provider is designed to be used when AWS credentials are configured.
It gracefully degrades when AWS is not available.
"""

import logging
from typing import Any

from app.cost.analyzer import CostProvider

logger = logging.getLogger(__name__)


class AWSCostProvider(CostProvider):
    """AWS cost data provider using boto3.

    Fetches:
    - EC2 instance pricing from AWS Price List API
    - Actual resource utilization from CloudWatch
    - EKS node group sizing recommendations
    """

    def __init__(self, region: str = "us-east-1") -> None:
        self._region = region
        self._pricing_client = None
        self._cloudwatch_client = None
        self._ec2_client = None
        self._available = False

        try:
            import boto3

            session = boto3.Session(region_name=region)
            self._pricing_client = session.client("pricing", region_name="us-east-1")
            self._cloudwatch_client = session.client("cloudwatch")
            self._ec2_client = session.client("ec2")
            self._available = True
            logger.info("AWS cost provider initialized for region %s", region)
        except Exception as e:
            logger.debug("AWS cost provider not available: %s", e)

    def is_available(self) -> bool:
        return self._available

    def get_resource_utilization(self, resource_name: str) -> dict:
        """Get resource utilization from CloudWatch metrics."""
        if not self._available:
            return {}

        try:
            # Query CloudWatch for CPU and memory utilization
            from datetime import datetime, timedelta, timezone

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)

            # Get CPU utilization
            cpu_response = self._cloudwatch_client.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": resource_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Average"],
            )

            cpu_data = cpu_response.get("Datapoints", [])
            avg_cpu = (
                sum(dp["Average"] for dp in cpu_data) / len(cpu_data) if cpu_data else 0
            )

            return {
                "resource_name": resource_name,
                "avg_cpu_percent": round(avg_cpu, 2),
                "datapoints": len(cpu_data),
                "source": "cloudwatch",
            }

        except Exception as e:
            logger.debug("Failed to get CloudWatch metrics: %s", e)
            return {}

    def get_pricing(self, resource_type: str) -> float | None:
        """Get pricing from AWS Price List API."""
        if not self._available:
            return None

        try:
            if resource_type == "ec2":
                # Get EC2 instance pricing
                response = self._pricing_client.get_products(
                    ServiceCode="AmazonEC2",
                    Filters=[
                        {
                            "Type": "TERM_MATCH",
                            "Field": "instanceType",
                            "Value": "t3.medium",
                        },
                        {
                            "Type": "TERM_MATCH",
                            "Field": "location",
                            "Value": "US East (N. Virginia)",
                        },
                    ],
                )
                if response.get("PriceList"):
                    import json

                    price_item = json.loads(response["PriceList"][0])
                    dimensions = price_item["terms"]["OnDemand"]
                    for dim in dimensions.values():
                        for price in dim["priceDimensions"].values():
                            return float(price["pricePerUnit"]["USD"])
            return None

        except Exception as e:
            logger.debug("Failed to get AWS pricing: %s", e)
            return None

    def get_cost_recommendations(self) -> list[dict[str, Any]]:
        """Generate cost recommendations based on AWS data."""
        if not self._available:
            return []

        recommendations = []

        try:
            # Get all EC2 instances
            response = self._ec2_client.describe_instances(
                Filters=[{"Name": "instance-state-name", "Value": "running"}]
            )

            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]

                    # Get utilization
                    utilization = self.get_resource_utilization(instance_id)
                    avg_cpu = utilization.get("avg_cpu_percent", 0)

                    # Recommend downsizing if CPU < 25%
                    if avg_cpu < 25:
                        recommendations.append(
                            {
                                "resource_name": instance_id,
                                "resource_type": "ec2_instance",
                                "current_type": instance_type,
                                "avg_cpu_percent": avg_cpu,
                                "recommendation": (
                                    f"Instance {instance_id} ({instance_type}) has "
                                    f"average CPU of {avg_cpu:.1f}%. Consider downsizing."
                                ),
                                "category": "rightsizing",
                            }
                        )

        except Exception as e:
            logger.debug("Failed to get AWS cost recommendations: %s", e)

        return recommendations
