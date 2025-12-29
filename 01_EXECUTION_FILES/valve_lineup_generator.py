#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valve Lineup Generator (P1-3)
Generate detailed valve operation sequences from valve_map.json.
"""

from typing import Dict, List
import json
from pathlib import Path


class ValveLineupGenerator:
    """Generate detailed valve operation sequences."""

    def __init__(self, valve_map_path: str = "valve_map.json"):
        """Load valve map."""
        with open(valve_map_path, "r", encoding="utf-8") as f:
            self.valve_map = json.load(f)

    def get_tank_valves(self, tank_id: str, action: str) -> Dict:
        """
        Get valve information for tank and action.
        """
        tanks = self.valve_map.get("tanks", {})

        if tank_id not in tanks:
            return {
                "found": False,
                "message": f"Tank {tank_id} not found in valve map",
                "valves": [],
                "sequence": [],
            }

        tank_data = tanks[tank_id]

        if action == "FILL":
            valves = tank_data.get("fill_valves", [])
            sequence = tank_data.get("valve_sequence_fill", [])
        elif action == "DISCHARGE":
            valves = tank_data.get("discharge_valves", [])
            sequence = tank_data.get("valve_sequence_discharge", [])
        else:
            return {
                "found": False,
                "message": f"Invalid action: {action}",
                "valves": [],
                "sequence": [],
            }

        return {
            "found": True,
            "tank_name": tank_data.get("name", tank_id),
            "location": tank_data.get("location", "Unknown"),
            "valves": valves,
            "vent_valves": tank_data.get("vent_valves", []),
            "emergency_valves": tank_data.get("emergency_valves", []),
            "sequence": sequence,
            "closing_sequence": tank_data.get("closing_sequence", []),
            "notes": tank_data.get("notes", ""),
        }

    def generate_valve_lineup_text(
        self, tank_id: str, action: str, step_number: int = 1
    ) -> str:
        """
        Generate human-readable valve lineup text.
        """
        valve_info = self.get_tank_valves(tank_id, action)

        if not valve_info["found"]:
            return f"[ERROR] {valve_info['message']}"

        text = f"\n{'=' * 80}\n"
        text += f"VALVE LINEUP - Step {step_number}\n"
        text += f"{'=' * 80}\n"
        text += f"Tank: {valve_info['tank_name']} ({tank_id})\n"
        text += f"Location: {valve_info['location']}\n"
        text += f"Action: {action}\n"

        if valve_info.get("notes"):
            text += f"\nWARNING:\n{valve_info['notes']}\n"

        text += "\n--- VALVE LIST ---\n"
        text += f"Vent Valves: {', '.join(valve_info['vent_valves'])}\n"
        text += f"{action} Valves: {', '.join(valve_info['valves'])}\n"
        text += f"Emergency Valves: {', '.join(valve_info['emergency_valves'])}\n"

        text += "\n--- OPERATION SEQUENCE ---\n"
        for i, step in enumerate(valve_info["sequence"], 1):
            text += f"{i}. {step}\n"

        text += "\n--- CLOSING SEQUENCE ---\n"
        for i, step in enumerate(valve_info["closing_sequence"], 1):
            text += f"{i}. {step}\n"

        text += f"{'=' * 80}\n"
        return text

    def enhance_ballast_sequence_with_valves(
        self,
        sequence_csv: str,
        output_path: str = "BALLAST_SEQUENCE_WITH_VALVES.md",
    ) -> None:
        """
        Enhance BALLAST_SEQUENCE.csv with detailed valve lineups.
        """
        import pandas as pd

        sequence_df = pd.read_csv(sequence_csv)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# BALLAST OPERATIONS - DETAILED VALVE LINEUPS\n\n")
            f.write(f"Generated from: {sequence_csv}\n\n")
            f.write("---\n\n")

            for _, row in sequence_df.iterrows():
                step = row["Step"]
                tank = row["Tank"]
                action = row["Action"]

                if action in ["FILL", "DISCHARGE"]:
                    valve_text = self.generate_valve_lineup_text(tank, action, step)
                    f.write(valve_text)
                    f.write("\n")

        print(f"[OK] Enhanced sequence with valve details: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Valve Lineup Generator")
    parser.add_argument("--sequence", required=True, help="Path to BALLAST_SEQUENCE.csv")
    parser.add_argument(
        "--valve_map", default="valve_map.json", help="Path to valve_map.json"
    )
    parser.add_argument(
        "--output", default="BALLAST_SEQUENCE_WITH_VALVES.md", help="Output file"
    )

    args = parser.parse_args()

    generator = ValveLineupGenerator(args.valve_map)
    generator.enhance_ballast_sequence_with_valves(args.sequence, args.output)
