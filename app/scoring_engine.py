"""
Core navigation scoring engine.
Extracted from nav.py; pure functions for scoring flight results.
"""

import math
import logging
from datetime import timedelta
from typing import Dict, List, Tuple, Optional
from geopy.distance import geodesic
from geopy.point import Point

logger = logging.getLogger(__name__)


class NavScoringEngine:
    """Encapsulates all scoring logic."""

    def __init__(self, config: Dict):
        """
        config: Dict with keys:
          - timing_penalty_per_second: float
          - off_course: {max_no_penalty_nm, max_penalty_distance_nm, max_penalty_points}
          - fuel_burn: {over_estimate_multiplier, under_estimate_threshold, under_estimate_multiplier}
          - secrets: {checkpoint_penalty, enroute_penalty, max_distance_miles}
        """
        self.config = config

    def haversine_distance(self, coord1: Dict, coord2: Dict) -> float:
        """Distance in nautical miles."""
        return geodesic(
            (coord1["lat"], coord1["lon"]),
            (coord2["lat"], coord2["lon"])
        ).nautical

    def calculate_bearing(self, coord1: Dict, coord2: Dict) -> float:
        """Bearing from coord1 to coord2 in degrees (0-360)."""
        point1 = Point(coord1["lat"], coord1["lon"])
        point2 = Point(coord2["lat"], coord2["lon"])
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
        delta_lon = lon2 - lon1
        x = math.sin(delta_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        return bearing

    def side_of_plane(self, point: Dict, checkpoint: Dict, plane_bearing: float) -> int:
        """Return 1 or -1 depending on which side of perpendicular plane point is."""
        point_bearing = self.calculate_bearing(checkpoint, point)
        angle_diff = (point_bearing - plane_bearing + 360) % 360
        return 1 if angle_diff < 180 else -1

    def interpolate_point(
        self, p1: Dict, p2: Dict, fraction: float
    ) -> Dict:
        """Linearly interpolate between two track points."""
        lat = p1["lat"] + fraction * (p2["lat"] - p1["lat"])
        lon = p1["lon"] + fraction * (p2["lon"] - p1["lon"])
        time_diff = (p2["time"] - p1["time"]).total_seconds()
        interpolated_time = p1["time"] + timedelta(seconds=fraction * time_diff)
        return {"lat": lat, "lon": lon, "time": interpolated_time}

    def detect_start_gate_crossing(
        self, track_points: List[Dict], start_gate: Dict
    ) -> Tuple[Optional[Dict], Optional[float]]:
        """
        Detect when aircraft crosses start gate.
        Returns (crossing_point, distance_nm) or (None, None).
        """
        TAKEOFF_SPEED_THRESHOLD = 5.0  # m/s (~9.7 knots)
        INITIAL_DISTANCE_THRESHOLD = 0.02
        MAX_DISTANCE_THRESHOLD = 0.10
        DISTANCE_INCREMENT = 0.01

        distance_threshold = INITIAL_DISTANCE_THRESHOLD
        time_span = (track_points[-1]["time"] - track_points[0]["time"]).total_seconds()
        time_limit = track_points[0]["time"] + timedelta(seconds=time_span * 0.5)

        while distance_threshold <= MAX_DISTANCE_THRESHOLD:
            candidate_points = []
            for point in track_points:
                if point["time"] > time_limit:
                    continue
                distance = self.haversine_distance(
                    {"lat": point["lat"], "lon": point["lon"]}, start_gate
                )
                is_takeoff = point["speed"] >= TAKEOFF_SPEED_THRESHOLD
                if distance <= distance_threshold and is_takeoff:
                    candidate_points.append((point, distance))

            if candidate_points:
                start_gate_closest, start_distance = min(
                    candidate_points, key=lambda x: x[1]
                )
                logger.info(
                    f"Start gate crossing detected at threshold {distance_threshold:.3f} NM"
                )
                return start_gate_closest, start_distance

            # No candidates; try without speed threshold
            candidate_points = [
                (point, self.haversine_distance(
                    {"lat": point["lat"], "lon": point["lon"]}, start_gate))
                for point in track_points
                if self.haversine_distance(
                    {"lat": point["lat"], "lon": point["lon"]}, start_gate
                ) <= distance_threshold and point["time"] <= time_limit
            ]
            if candidate_points:
                start_gate_closest, start_distance = min(
                    candidate_points, key=lambda x: x[1]
                )
                logger.info(
                    f"Start gate crossing detected (closest point) at {distance_threshold:.3f} NM"
                )
                return start_gate_closest, start_distance

            distance_threshold += DISTANCE_INCREMENT

        logger.error(f"No start gate crossing found within {MAX_DISTANCE_THRESHOLD} NM")
        return None, None

    def find_checkpoint_crossing(
        self,
        track_points: List[Dict],
        checkpoint: Dict,
        previous_point: Dict,
        previous_time,
    ) -> Tuple[Optional[Dict], float, str, bool]:
        """
        Find how aircraft approached checkpoint.
        Returns (timing_point, distance_nm, method, within_025_nm)
        
        Args:
            previous_time: datetime object or float (timestamp) of previous checkpoint
        """
        CHECKPOINT_RADIUS_NM = 0.25

        flight_path_bearing = self.calculate_bearing(previous_point, checkpoint)
        plane_bearing = (flight_path_bearing + 90) % 360

        crossing_found = False
        crossing_point = None
        crossing_distance = float("inf")
        plane_crossed = False
        plane_crossing_time = None
        timing_point = None

        # Step 1: Look for perpendicular plane crossing (CTP)
        for j in range(len(track_points) - 1):
            p1 = track_points[j]
            p2 = track_points[j + 1]
            side1 = self.side_of_plane(p1, checkpoint, plane_bearing)
            side2 = self.side_of_plane(p2, checkpoint, plane_bearing)

            if side1 != side2:
                # Plane crossed perpendicular line
                bearing1 = self.calculate_bearing(checkpoint, p1)
                bearing2 = self.calculate_bearing(checkpoint, p2)
                angle_diff1 = (bearing1 - plane_bearing + 360) % 360
                angle_diff2 = (bearing2 - plane_bearing + 360) % 360

                if angle_diff1 > 180:
                    angle_diff1 -= 360
                if angle_diff2 > 180:
                    angle_diff2 -= 360

                if abs(angle_diff1 - angle_diff2) < 1e-10:
                    fraction = 0.5
                else:
                    fraction = abs(angle_diff1) / abs(angle_diff1 - angle_diff2)

                temp_crossing_point = self.interpolate_point(p1, p2, fraction)
                temp_crossing_distance = self.haversine_distance(
                    temp_crossing_point, checkpoint
                )
                temp_crossing_time = temp_crossing_point["time"]

                if not plane_crossed and temp_crossing_time > previous_time:
                    plane_crossed = True
                    plane_crossing_time = temp_crossing_time

                # CTP: Must be within 0.25 NM and after previous checkpoint
                if (
                    temp_crossing_distance <= CHECKPOINT_RADIUS_NM
                    and p1["time"] <= temp_crossing_time <= p2["time"]
                    and temp_crossing_time > previous_time
                ):
                    crossing_found = True
                    crossing_point = temp_crossing_point
                    crossing_distance = temp_crossing_distance
                    crossing_time = temp_crossing_point["time"]

                    # Snap to nearest GPX point
                    time_diff_p1 = abs((p1["time"] - crossing_time).total_seconds())
                    time_diff_p2 = abs((p2["time"] - crossing_time).total_seconds())
                    timing_point = p1 if time_diff_p1 < time_diff_p2 else p2
                    break

        # Step 2: If CTP not found, look for radius entry (Radius Entry)
        if not crossing_found and plane_crossed:
            for j in range(len(track_points)):
                p = track_points[j]
                if p["time"] > plane_crossing_time:
                    distance = self.haversine_distance(
                        {"lat": p["lat"], "lon": p["lon"]}, checkpoint
                    )
                    if distance <= CHECKPOINT_RADIUS_NM:
                        crossing_found = True
                        crossing_distance = distance
                        timing_point = {"lat": p["lat"], "lon": p["lon"]}
                        crossing_time = p["time"]
                        break

        # Step 3: If still not found, use closest point approach (PCA)
        if not crossing_found:
            valid_points = [p for p in track_points if p["time"] > previous_time]
            if not valid_points:
                logger.error(f"No track points after previous checkpoint time")
                return None, float("inf"), "PCA", False

            closest_point = min(
                valid_points,
                key=lambda p: self.haversine_distance(
                    {"lat": p["lat"], "lon": p["lon"]}, checkpoint
                ),
            )
            crossing_distance = self.haversine_distance(
                {"lat": closest_point["lat"], "lon": closest_point["lon"]},
                checkpoint,
            )
            timing_point = {"lat": closest_point["lat"], "lon": closest_point["lon"]}
            crossing_time = closest_point["time"]

        # Determine method and penalty status
        if crossing_found and crossing_distance <= CHECKPOINT_RADIUS_NM:
            method = "CTP" if crossing_point else "Radius Entry"
            within_025_nm = True
        else:
            method = "PCA"
            within_025_nm = crossing_distance <= CHECKPOINT_RADIUS_NM

        return timing_point, crossing_distance, method, within_025_nm

    def calculate_leg_score(
        self,
        actual_time: float,
        estimated_time: float,
        distance_nm: float,
        within_025_nm: bool,
    ) -> Tuple[float, float]:
        """
        Calculate score for a single leg.
        Returns (leg_score, off_course_penalty)
        
        Off-course penalty per Red Book:
        - 0 to checkpoint_radius: 0 points
        - (radius + 0.01) to 5.0 NM: Linear from 100 to 600 points
        """
        cfg = self.config["scoring"]

        # Timing penalty
        deviation = actual_time - estimated_time
        leg_score = abs(deviation) * cfg.get("timing_penalty_per_second", 1.0)

        # Off-course penalty (Red Book v0.4.6)
        off_course_penalty = 0
        if not within_025_nm:
            off_course_cfg = cfg.get("off_course", {})
            checkpoint_radius = off_course_cfg.get("checkpoint_radius_nm", 0.25)
            min_penalty = off_course_cfg.get("min_penalty", 100)
            max_penalty = off_course_cfg.get("max_penalty", 600)
            max_distance = off_course_cfg.get("max_distance_nm", 5.0)
            
            # Threshold starts at (radius + 0.01)
            threshold_distance = checkpoint_radius + 0.01

            if threshold_distance <= distance_nm <= max_distance:
                # Linear interpolation from threshold to max_distance
                fraction = (distance_nm - threshold_distance) / (
                    max_distance - threshold_distance
                )
                off_course_penalty = min_penalty + fraction * (max_penalty - min_penalty)
            elif distance_nm > max_distance:
                # Beyond max distance: apply max penalty
                off_course_penalty = max_penalty

        return leg_score, off_course_penalty

    def calculate_fuel_penalty(
        self, estimated_fuel: float, actual_fuel: float
    ) -> float:
        """
        Calculate fuel burn penalty per Red Book v0.4.6.
        
        Error = (estimated - actual) / estimated
        - Underestimate (used MORE fuel, error < 0): 500 multiplier, NO threshold
        - Overestimate (used LESS fuel, error > 0): 250 multiplier, 10% threshold
        """
        cfg = self.config["scoring"]["fuel_burn"]

        if estimated_fuel == 0:
            return 0

        # Error calculation: (estimated - actual) / estimated
        fuel_error = (estimated_fuel - actual_fuel) / estimated_fuel

        if fuel_error < 0:
            # Underestimate: used MORE fuel than planned (negative error)
            # 500 multiplier, NO threshold
            multiplier = cfg.get("under_estimate_multiplier", 500)
            penalty = multiplier * (math.exp(abs(fuel_error)) - 1)
        elif fuel_error > cfg.get("over_estimate_threshold", 0.1):
            # Overestimate: used LESS fuel, but error exceeds 10% threshold
            # 250 multiplier, 10% threshold
            multiplier = cfg.get("over_estimate_multiplier", 250)
            penalty = multiplier * (math.exp(fuel_error) - 1)
        else:
            # Overestimate within 10% tolerance: no penalty
            penalty = 0

        return penalty

    def calculate_secrets_penalty(
        self, missed_checkpoint: int, missed_enroute: int
    ) -> Tuple[float, float]:
        """Calculate secrets penalties."""
        cfg = self.config["scoring"]["secrets"]
        checkpoint_penalty = missed_checkpoint * cfg.get("checkpoint_penalty", 20)
        enroute_penalty = missed_enroute * cfg.get("enroute_penalty", 10)
        return checkpoint_penalty, enroute_penalty

    def calculate_overall_score(
        self,
        checkpoint_scores: List[Tuple[float, float]],  # (leg_score, off_course)
        total_time_score: float,
        fuel_penalty: float,
        checkpoint_secrets_penalty: float,
        enroute_secrets_penalty: float,
    ) -> float:
        """Sum all penalties to get overall score (lower is better)."""
        checkpoint_total = sum(
            leg + off_course for leg, off_course in checkpoint_scores
        )
        overall = (
            checkpoint_total
            + total_time_score
            + fuel_penalty
            + checkpoint_secrets_penalty
            + enroute_secrets_penalty
        )
        return overall
