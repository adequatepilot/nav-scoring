"""
Enhanced PDF Report Generator for NAV Scoring Results.
Creates professional, print-friendly PDFs with advanced map visualizations.
"""

import logging
import io
import html
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Matplotlib imports - moved to functions that need them
# matplotlib is only required for generating maps, not for PDF generation

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)

# ===== CONSTANTS =====
CHECKPOINT_RADIUS_NM = 0.25
COLOR_PLANNED_ROUTE = '#0066CC'  # Blue
COLOR_ACTUAL_TRACK = '#CC0000'   # Red
COLOR_START_GATE = '#00AA00'     # Green
COLOR_CHECKPOINT = '#FF6600'     # Orange


def nm_to_decimal_degrees(distance_nm: float, latitude: float) -> float:
    """Convert nautical miles to decimal degrees at given latitude."""
    import math
    # 1 degree latitude = 60 NM (constant)
    degrees_lat = distance_nm / 60.0
    # 1 degree longitude = 60 NM * cos(latitude) (varies with latitude)
    cos_lat = math.cos(math.radians(latitude))
    if cos_lat > 0:
        degrees_lon = distance_nm / (60.0 * cos_lat)
    else:
        degrees_lon = distance_nm / 60.0
    return max(degrees_lat, degrees_lon)


def calculate_perpendicular_distance(
    point: Dict,
    line_start: Dict,
    line_end: Dict
) -> Tuple[float, Dict]:
    """
    Calculate perpendicular distance from a point to a line in nautical miles.
    Also returns the foot of the perpendicular (closest point on the line).
    
    Args:
        point: Point with 'lat', 'lon' keys
        line_start: Line start point with 'lat', 'lon' keys
        line_end: Line end point with 'lat', 'lon' keys
    
    Returns:
        (distance_nm, foot_of_perpendicular_dict)
    """
    import math
    
    # Get latitude for conversion
    avg_lat = (point['lat'] + line_start['lat'] + line_end['lat']) / 3
    
    # Convert lat/lon to NM (treating as a 2D Cartesian system)
    # Latitude: 1 degree = 60 NM
    # Longitude: 1 degree = 60 NM * cos(latitude)
    cos_lat = math.cos(math.radians(avg_lat))
    
    # Convert to NM coordinates
    p_lat_nm = point['lat'] * 60
    p_lon_nm = point['lon'] * 60 * cos_lat
    
    ls_lat_nm = line_start['lat'] * 60
    ls_lon_nm = line_start['lon'] * 60 * cos_lat
    
    le_lat_nm = line_end['lat'] * 60
    le_lon_nm = line_end['lon'] * 60 * cos_lat
    
    # Vector from line_start to line_end
    line_vec = [le_lon_nm - ls_lon_nm, le_lat_nm - ls_lat_nm]
    # Vector from line_start to point
    point_vec = [p_lon_nm - ls_lon_nm, p_lat_nm - ls_lat_nm]
    
    # Calculate parameter t for foot of perpendicular
    line_len_sq = line_vec[0] * line_vec[0] + line_vec[1] * line_vec[1]
    if line_len_sq == 0:
        # Start and end are same point
        foot_lon_nm = ls_lon_nm
        foot_lat_nm = ls_lat_nm
        distance_nm = math.sqrt(point_vec[0] * point_vec[0] + point_vec[1] * point_vec[1])
    else:
        dot_product = point_vec[0] * line_vec[0] + point_vec[1] * line_vec[1]
        t = dot_product / line_len_sq
        # Clamp t to [0, 1] to keep foot on the line segment
        t = max(0, min(1, t))
        
        # Calculate foot coordinates in NM
        foot_lon_nm = ls_lon_nm + t * line_vec[0]
        foot_lat_nm = ls_lat_nm + t * line_vec[1]
        
        # Calculate perpendicular distance
        foot_vec = [foot_lon_nm - p_lon_nm, foot_lat_nm - p_lat_nm]
        distance_nm = math.sqrt(foot_vec[0] * foot_vec[0] + foot_vec[1] * foot_vec[1])
    
    # Convert foot back to lat/lon
    foot_lat = foot_lat_nm / 60
    foot_lon = foot_lon_nm / (60 * cos_lat) if cos_lat > 0 else foot_lon_nm / 60
    
    foot = {'lat': foot_lat, 'lon': foot_lon}
    
    return distance_nm, foot


def get_bounding_box(points: List[Dict], padding_nm: float = 1.0) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box for a list of points with padding.
    Returns (min_lat, min_lon, max_lat, max_lon)
    """
    if not points:
        return (0, 0, 1, 1)
    
    lats = [p.get('lat', 0) for p in points]
    lons = [p.get('lon', 0) for p in points]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Add padding
    avg_lat = (min_lat + max_lat) / 2
    padding_degrees = nm_to_decimal_degrees(padding_nm, avg_lat)
    
    min_lat -= padding_degrees
    max_lat += padding_degrees
    min_lon -= padding_degrees
    max_lon += padding_degrees
    
    return (min_lat, min_lon, max_lat, max_lon)


def add_direction_arrows(ax, points: List[Dict], interval: int = 10, 
                        color: str = 'red', alpha: float = 0.7, 
                        arrow_size: float = 0.01):
    """
    Add directional arrows along a track to indicate direction of travel.
    
    Args:
        ax: Matplotlib axis to draw on
        points: List of points with 'lat' and 'lon' keys
        interval: Sample every N points (e.g., 10 = every 10th point)
        color: Arrow color
        alpha: Arrow transparency
        arrow_size: Size of arrow head (in plot units)
    """
    from matplotlib.patches import FancyArrowPatch
    import math
    
    if len(points) < 2:
        return
    
    # Sample points at regular intervals
    sampled_indices = list(range(0, len(points) - 1, max(1, interval)))
    
    for idx in sampled_indices:
        if idx + 1 >= len(points):
            break
        
        current = points[idx]
        next_point = points[idx + 1]
        
        lon1, lat1 = current['lon'], current['lat']
        lon2, lat2 = next_point['lon'], next_point['lat']
        
        # Calculate direction vector
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        # Skip if points are too close
        if abs(dlon) < 1e-6 and abs(dlat) < 1e-6:
            continue
        
        # Normalize direction
        magnitude = math.sqrt(dlon**2 + dlat**2)
        dlon_norm = dlon / magnitude
        dlat_norm = dlat / magnitude
        
        # Draw arrow from current point in direction of next point
        arrow = FancyArrowPatch(
            (lon1, lat1),
            (lon1 + dlon_norm * arrow_size, lat1 + dlat_norm * arrow_size),
            arrowstyle='->', mutation_scale=15, 
            color=color, alpha=alpha, linewidth=1.5, zorder=4
        )
        ax.add_patch(arrow)


def generate_full_route_map(
    track_points: List[Dict],
    start_gate: Dict,
    checkpoints: List[Dict],
    output_path: Path,
    figure_size: Tuple[float, float] = (10, 8)
):
    """
    Generate a comprehensive route map showing:
    - Planned route (start gate → checkpoints as straight lines)
    - Actual GPS track
    - All checkpoints marked
    
    Args:
        track_points: List of actual GPS track points
        start_gate: Start gate location (lat, lon)
        checkpoints: List of checkpoints in order
        output_path: Path to save the map image
        figure_size: Figure dimensions in inches
    """
    # Import matplotlib only when needed
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Circle, FancyArrowPatch
    import numpy as np
    
    fig, ax = plt.subplots(figsize=figure_size, dpi=100)
    
    # Get bounding box for all points
    all_points = [start_gate] + checkpoints + track_points
    min_lat, min_lon, max_lat, max_lon = get_bounding_box(all_points, padding_nm=1.5)
    
    # Plot actual track
    if track_points:
        track_lats = [p['lat'] for p in track_points]
        track_lons = [p['lon'] for p in track_points]
        ax.plot(track_lons, track_lats, color=COLOR_ACTUAL_TRACK, linewidth=1.5, 
                alpha=0.7, label='Actual Track', zorder=2)
        
        # Add direction-of-travel arrows along the track
        # Sample every ~15 seconds of data (roughly every 15-20 points at 1Hz)
        arrow_interval = max(1, len(track_points) // 20)  # ~20 arrows across route
        add_direction_arrows(ax, track_points, interval=arrow_interval, 
                           color=COLOR_ACTUAL_TRACK, alpha=0.8, arrow_size=0.015)
    
    # Plot planned route (straight lines between waypoints)
    route_lats = [start_gate['lat']] + [cp['lat'] for cp in checkpoints]
    route_lons = [start_gate['lon']] + [cp['lon'] for cp in checkpoints]
    ax.plot(route_lons, route_lats, color=COLOR_PLANNED_ROUTE, linewidth=2, 
            linestyle='--', alpha=0.8, label='Planned Route', zorder=1)
    
    # Plot start gate
    ax.scatter(start_gate['lon'], start_gate['lat'], c=COLOR_START_GATE, s=200, 
              marker='s', label='Start Gate', zorder=5, edgecolors='black', linewidth=1.5)
    ax.text(start_gate['lon'], start_gate['lat'] - 0.005, 'START', 
           fontsize=8, ha='center', fontweight='bold')
    
    # Plot checkpoints
    cp_lons = [cp['lon'] for cp in checkpoints]
    cp_lats = [cp['lat'] for cp in checkpoints]
    ax.scatter(cp_lons, cp_lats, c=COLOR_CHECKPOINT, s=150, marker='o', 
              label='Checkpoints', zorder=5, edgecolors='black', linewidth=1.5)
    
    # Label checkpoints
    for i, cp in enumerate(checkpoints, 1):
        ax.text(cp['lon'], cp['lat'] + 0.005, f"CP {i}", 
               fontsize=8, ha='center', fontweight='bold')
    
    # Set map extent
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    
    # Formatting
    ax.set_xlabel('Longitude', fontsize=10, fontweight='bold')
    ax.set_ylabel('Latitude', fontsize=10, fontweight='bold')
    ax.set_title('Complete Flight Route - Planned vs Actual', fontsize=12, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend(loc='upper left', fontsize=9, framealpha=0.95)
    ax.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    logger.info(f"Full route map saved: {output_path}")


def generate_checkpoint_detail_map(
    track_points: List[Dict],
    checkpoint: Dict,
    checkpoint_index: int,
    output_path: Path,
    radius_nm: float = CHECKPOINT_RADIUS_NM,
    figure_size: Tuple[float, float] = (8, 8),
    start_gate: Optional[Dict] = None,
    previous_checkpoint: Optional[Dict] = None
):
    """
    Generate a detailed map for a single checkpoint showing:
    - Actual GPS track as it approaches and crosses
    - Checkpoint location
    - Maximum radius circle
    - Closest point of approach
    - Perpendicular line ("the plane") from actual track to intended course
    
    Args:
        track_points: List of all GPS track points
        checkpoint: Checkpoint data (lat, lon, name)
        checkpoint_index: Checkpoint number (1-indexed)
        output_path: Path to save the map
        radius_nm: Checkpoint radius in nautical miles
        figure_size: Figure dimensions
        start_gate: Start gate location (used if checkpoint_index == 1)
        previous_checkpoint: Previous checkpoint (used if checkpoint_index > 1)
    """
    # Import matplotlib only when needed
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Circle, FancyArrowPatch
    import numpy as np
    
    fig, ax = plt.subplots(figsize=figure_size, dpi=100)
    
    # Calculate search area (2x radius for visibility)
    search_radius_nm = radius_nm * 2.5
    padding_degrees = nm_to_decimal_degrees(search_radius_nm, checkpoint['lat'])
    
    min_lat = checkpoint['lat'] - padding_degrees
    max_lat = checkpoint['lat'] + padding_degrees
    min_lon = checkpoint['lon'] - padding_degrees
    max_lon = checkpoint['lon'] + padding_degrees
    
    # Filter track points near checkpoint
    nearby_points = [
        p for p in track_points
        if min_lat <= p['lat'] <= max_lat and min_lon <= p['lon'] <= max_lon
    ]
    
    # Plot track near checkpoint
    if nearby_points:
        track_lats = [p['lat'] for p in nearby_points]
        track_lons = [p['lon'] for p in nearby_points]
        ax.plot(track_lons, track_lats, color=COLOR_ACTUAL_TRACK, linewidth=2,
               alpha=0.8, label='GPS Track', zorder=3)
        # Plot track points as dots
        ax.scatter(track_lons, track_lats, c=COLOR_ACTUAL_TRACK, s=10, 
                  alpha=0.6, zorder=2)
    
    # Draw checkpoint radius circle
    radius_degrees = nm_to_decimal_degrees(radius_nm, checkpoint['lat'])
    circle = Circle((checkpoint['lon'], checkpoint['lat']), radius_degrees,
                   fill=False, edgecolor=COLOR_CHECKPOINT, linewidth=2,
                   linestyle='--', alpha=0.7, label=f'Radius ({radius_nm:.2f} NM)')
    ax.add_patch(circle)
    
    # Find closest point of approach
    closest_point = None
    closest_distance_nm = float('inf')
    if track_points:
        for p in track_points:
            # Calculate distance in NM
            lat_diff_nm = (p['lat'] - checkpoint['lat']) * 60
            lon_diff_nm = (p['lon'] - checkpoint['lon']) * 60 * np.cos(np.radians(checkpoint['lat']))
            distance_nm = np.sqrt(lat_diff_nm**2 + lon_diff_nm**2)
            if distance_nm < closest_distance_nm:
                closest_distance_nm = distance_nm
                closest_point = p
    
    # Plot checkpoint
    ax.scatter(checkpoint['lon'], checkpoint['lat'], c=COLOR_CHECKPOINT, s=300,
              marker='*', label='Checkpoint', zorder=5, edgecolors='black', linewidth=2)
    
    # Plot closest point if found
    if closest_point:
        ax.scatter(closest_point['lon'], closest_point['lat'], c='yellow', s=150,
                  marker='X', label=f'Closest Approach ({closest_distance_nm:.3f} NM)',
                  zorder=5, edgecolors='black', linewidth=1)
        
        # Calculate and draw perpendicular line to intended course ("the plane")
        # Intended course: from start_gate (or previous_checkpoint) to checkpoint
        intended_start = None
        if checkpoint_index == 1 and start_gate:
            intended_start = start_gate
        elif checkpoint_index > 1 and previous_checkpoint:
            intended_start = previous_checkpoint
        
        if intended_start:
            perpendicular_distance_nm, foot_of_perpendicular = calculate_perpendicular_distance(
                closest_point, intended_start, checkpoint
            )
            
            # Draw perpendicular line from closest point to foot of perpendicular
            ax.plot(
                [closest_point['lon'], foot_of_perpendicular['lon']],
                [closest_point['lat'], foot_of_perpendicular['lat']],
                color='#FF1493',  # Deep pink for perpendicular line
                linewidth=2.5,
                linestyle='--',
                alpha=0.8,
                label=f'"The Plane" ({perpendicular_distance_nm:.3f} NM)',
                zorder=4
            )
            
            # Mark foot of perpendicular
            ax.scatter(foot_of_perpendicular['lon'], foot_of_perpendicular['lat'],
                      c='#FF1493', s=100, marker='|', zorder=5, linewidth=2)
            
            # Add distance label on the perpendicular line
            # Calculate midpoint of perpendicular for label placement
            mid_lat = (closest_point['lat'] + foot_of_perpendicular['lat']) / 2
            mid_lon = (closest_point['lon'] + foot_of_perpendicular['lon']) / 2
            
            # Offset label slightly perpendicular to the perpendicular line for readability
            lat_offset = (foot_of_perpendicular['lon'] - closest_point['lon']) * 0.001
            lon_offset = (foot_of_perpendicular['lat'] - closest_point['lat']) * 0.001
            
            ax.text(
                mid_lon + lon_offset, mid_lat + lat_offset,
                f'{perpendicular_distance_nm:.3f} NM',
                fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FF1493', alpha=0.7, edgecolor='black'),
                ha='center', va='center', zorder=6, color='white'
            )
    
    # Set map extent
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    
    # Formatting
    ax.set_xlabel('Longitude', fontsize=9, fontweight='bold')
    ax.set_ylabel('Latitude', fontsize=9, fontweight='bold')
    within_radius = closest_distance_nm <= radius_nm if closest_point else False
    status = "✓ INSIDE" if within_radius else "✗ OUTSIDE"
    
    ax.set_title(f"CP {checkpoint_index}: {checkpoint['name']} - {status}", 
                fontsize=11, fontweight='bold', pad=12)
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend(loc='upper left', fontsize=8, framealpha=0.95)
    ax.set_aspect('equal', adjustable='box')
    
    # Add info box
    info_text = f"Coords: {checkpoint['lat']:.4f}, {checkpoint['lon']:.4f}\n"
    if closest_point:
        info_text += f"Closest: {closest_distance_nm:.3f} NM"
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
           fontsize=8, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    logger.info(f"Checkpoint detail map saved: {output_path}")


def generate_enhanced_pdf_report(
    result_data: Dict,
    nav_data: Dict,
    pairing_data: Dict,
    start_gate: Dict,
    checkpoints: List[Dict],
    track_points: List[Dict],
    full_route_map_path: Path,
    checkpoint_maps_paths: List[Path],
    output_path: Path
):
    """
    Generate a professional NAV scoring report PDF with improved formatting.
    
    Args:
        result_data: Flight results with penalties and scores
        nav_data: NAV information
        pairing_data: Pilot and observer information
        start_gate: Start gate location
        checkpoints: List of checkpoints
        track_points: GPS track points
        full_route_map_path: Path to full route map image
        checkpoint_maps_paths: List of paths to checkpoint detail maps
        output_path: Output PDF path
    """
    
    # Use landscape orientation for better table width (11x8.5)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(letter),
        topMargin=0.4*inch,
        bottomMargin=0.4*inch,
        leftMargin=0.4*inch,
        rightMargin=0.4*inch
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # ===== PAGE 1: TITLE AND HEADER =====
    
    nav_name = nav_data.get('name', 'NAV Scoring Report')
    story.append(Paragraph(nav_name, styles['Title']))
    story.append(Spacer(1, 0.15*inch))
    
    # Header info
    flight_started = result_data.get('flight_started_at', 'N/A')
    overall_score = result_data.get('overall_score', 0)
    pilot_name = pairing_data.get('pilot_name', 'Unknown')
    observer_name = pairing_data.get('observer_name', 'Unknown')
    
    header_info = f"""Flight Started: {flight_started} | Overall Score: {overall_score:.0f} points | Pilot: {pilot_name} | Observer: {observer_name}"""
    
    story.append(Paragraph(header_info, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # ===== RESULTS SUMMARY TABLE =====
    
    story.append(Paragraph("Checkpoint Results", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    # Build results table with improved column structure including "Method"
    table_data = [
        ['CP', 'Name', 'Method', 'Est Time', 'Act Time', 'Dev', 'Distance\n(NM)', 'Timing\nScore', 'Off-Course\nPenalty', 'Leg\nTotal'],
    ]
    
    # Checkpoint rows - plain text strings only
    for i, cp in enumerate(result_data.get('checkpoint_results', []), 1):
        est_time = f"{int(cp['estimated_time']//60):02d}:{int(cp['estimated_time']%60):02d}"
        act_time = f"{int(cp['actual_time']//60):02d}:{int(cp['actual_time']%60):02d}"
        dev = f"{cp.get('deviation', 0):+.0f}s"
        distance = f"{cp.get('distance_nm', 0):.3f}"
        points = f"{cp.get('leg_score', 0):.0f}"
        penalty = f"{cp.get('off_course_penalty', 0):.0f}"
        total = f"{cp.get('leg_score', 0) + cp.get('off_course_penalty', 0):.0f}"
        method = str(cp.get('method', 'N/A'))
        cp_name = str(cp.get('name', f'CP {i}'))[:12]  # Truncate long names
        
        table_data.append([
            str(i),
            cp_name,
            method,
            est_time,
            act_time,
            dev,
            distance,
            points,
            penalty,
            total
        ])
    
    # Summary rows
    total_time_dev = f"{result_data.get('total_time_deviation', 0):+.0f}s"
    total_time_penalty = f"{result_data.get('total_time_penalty', 0):.0f}"
    time_score = f"{result_data.get('total_time_score', 0):.0f}"
    fuel_penalty = f"{result_data.get('fuel_penalty', 0):.0f}"
    cp_secrets = f"{result_data.get('checkpoint_secrets_penalty', 0):.0f}"
    enroute_secrets = f"{result_data.get('enroute_secrets_penalty', 0):.0f}"
    
    # Blank row for spacing
    table_data.append(['', '', '', '', '', '', '', '', '', ''])
    
    # Format total times as HH:MM:SS
    est_total_time = result_data.get('estimated_total_time', 0)
    act_total_time = result_data.get('actual_total_time', 0)
    est_total_str = f"{int(est_total_time//3600):02d}:{int((est_total_time%3600)//60):02d}:{int(est_total_time%60):02d}"
    act_total_str = f"{int(act_total_time//3600):02d}:{int((act_total_time%3600)//60):02d}:{int(act_total_time%60):02d}"
    
    # Total Time row (full format, appears before TIMING SUBTOTAL)
    table_data.append(['', 'Total Time', '', est_total_str, act_total_str, total_time_dev, '', '', '', ''])
    
    # Calculate column widths for landscape (11" - margins = 10.2")
    col_widths = [
        0.35*inch,  # CP number
        1.5*inch,   # Name (increased to accommodate longer checkpoint names)
        0.65*inch,  # Method (reduced slightly)
        0.6*inch,   # Est Time (reduced slightly)
        0.6*inch,   # Act Time (reduced slightly)
        0.5*inch,   # Deviation (reduced slightly)
        0.65*inch,  # Distance
        0.7*inch,   # Timing Score
        0.75*inch,  # Off-Course Penalty
        0.7*inch,   # Leg Total
    ]
    
    results_table = Table(table_data, colWidths=col_widths)
    
    # Professional table styling
    table_style = TableStyle([
        # Header row - dark blue background
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        
        # Data rows - alternating light colors
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # CP column centered
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Rest centered
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        
        # Alternating row colors (light gray for even rows)
        ('BACKGROUND', (0, 2), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
        
        # Grid lines
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#003366')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#003366')),
        
        # Format Total Time row (last row before summary table)
        ('BACKGROUND', (0, len(table_data)-1), (-1, len(table_data)-1), colors.HexColor('#F5F5F5')),
        ('FONTNAME', (0, len(table_data)-1), (-1, len(table_data)-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, len(table_data)-1), (-1, len(table_data)-1), 8),
    ])
    
    results_table.setStyle(table_style)
    
    story.append(results_table)
    story.append(Spacer(1, 0.2*inch))
    
    # ===== PAGE 2: ROUTE MAP =====
    
    story.append(PageBreak())
    story.append(Paragraph("Flight Route Map", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Blue dashed line: Planned route | Red line: Actual track | Red arrows: Direction of travel", styles['Normal']))
    story.append(Spacer(1, 0.15*inch))
    
    # Add full route map if it exists
    if full_route_map_path and Path(full_route_map_path).exists():
        try:
            # Set explicit dimensions maintaining 10:8 aspect ratio (6 inches wide x 4.8 inches tall)
            # This prevents stretching and fits properly on landscape pages
            img = Image(str(full_route_map_path), width=6.5*inch, height=5.2*inch)
            story.append(img)
        except Exception as e:
            logger.error(f"Failed to add full route map: {e}")
            story.append(Paragraph(f"[Map unavailable: {str(e)}]", styles['Normal']))
    else:
        story.append(Paragraph("[Route map not available]", styles['Normal']))
    
    # ===== CHECKPOINT DETAIL MAPS =====
    
    # Add checkpoint detail maps if available
    checkpoint_maps = [Path(p) for p in checkpoint_maps_paths] if checkpoint_maps_paths else []
    
    if checkpoint_maps:
        for i, cp_map_path in enumerate(checkpoint_maps):
            if cp_map_path.exists():
                # Add page break before each checkpoint map
                story.append(PageBreak())
                
                cp_num = i + 1
                cp_name = checkpoints[i]['name'] if i < len(checkpoints) else f"CP {cp_num}"
                story.append(Paragraph(f"Checkpoint {cp_num}: {cp_name}", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                
                # Add checkpoint detail map - sized to fit landscape page
                try:
                    img = Image(str(cp_map_path), width=6.5*inch, height=6.5*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.1*inch))
                except Exception as e:
                    logger.warning(f"Failed to add checkpoint {cp_num} map: {e}")
                    story.append(Paragraph(f"[Checkpoint map unavailable: {str(e)}]", styles['Normal']))
    
    # Build PDF
    try:
        doc.build(story)
        logger.info(f"Enhanced PDF report generated successfully: {output_path}")
    except Exception as e:
        logger.error(f"Error building PDF: {e}")
        raise
