"""
report_service.py

Generates structured threat reports.
"""

from datetime import datetime


class ReportService:

    def __init__(self):
        self.report_count = 0

    def generate_report(self, threat):

        """
        Generate a report for one threat object.

        Args:
            threat (dict)

        Returns:
            dict
        """

        self.report_count += 1

        report = {

    "report_id": self.report_count,

    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

    "camera_id": threat.get("camera_id", -1),

    "camera_name": threat.get("camera_name", "Unknown Camera"),

    "track_id": threat.get("track_id", -1),

    "object": threat.get("class_name", "Unknown"),

    "confidence": threat.get("confidence", 0),

    "severity": threat.get("severity", "NONE"),

    "duration": threat.get("duration", 0),

    "bbox": threat.get("bbox", []),

    "status": "ACTIVE"
}

        return report

    def print_report(self, report):

        print("\n" + "=" * 45)

        print("         THREAT REPORT")

        print("=" * 45)

        print(f"Report ID : {report['report_id']}")

        print(f"Time      : {report['timestamp']}")
        print(f"Camera ID : {report['camera_id']}")

        print(f"Camera    : {report['camera_name']}")

        print(f"Track ID  : {report['track_id']}")

        print(f"Object    : {report['object']}")

        print(f"Confidence: {report['confidence']:.2f}")

        print(f"Severity  : {report['severity']}")

        print(f"Duration  : {report['duration']} sec")

        print(f"Status    : {report['status']}")

        print("=" * 45)

 