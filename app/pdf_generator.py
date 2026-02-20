"""
Enhanced PDF Report Generator for NAV Scoring Results.
Creates professional, print-friendly PDFs with advanced map visualizations.
"""

import logging
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle
import numpy as np

from reportlab.lib.pagesizes import letter
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
    # 1 degree latitude = 60 NM (constant)
    degrees_lat = distance_nm / 60.0
    # 1 degree longitude = 60 NM * cos(latitude) (varies with latitude)
    cos_lat = np.cos(np.radians(latitude))
    if cos_lat > 0:
        degrees_lon = distance_nm / (60.0 * cos_lat)
    else:
        degrees_lon = distance_nm / 60.0
    return max(degrees_lat, degrees_lon)


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
    figure_size: Tuple[float, float] = (8, 8)
):
    """
    Generate a detailed map for a single checkpoint showing:
    - Actual GPS track as it approaches and crosses
    - Checkpoint location
    - Maximum radius circle
    - Closest point of approach
    
    Args:
        track_points: List of all GPS track points
        checkpoint: Checkpoint data (lat, lon, name)
        checkpoint_index: Checkpoint number (1-indexed)
        output_path: Path to save the map
        radius_nm: Checkpoint radius in nautical miles
        figure_size: Figure dimensions
    """
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
    Generate a professional, comprehensive NAV scoring report PDF.
    
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
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # ===== HEADER SECTION =====
    
    # Title with NAV name
    title_style = ParagraphStyle(
        'NavTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#003366'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph(f"{nav_data['name']}", title_style))
    
    # Flight info header
    header_table_data = [
        [
            f"<b>Flight Started:</b> {result_data.get('flight_started_at', 'N/A')}",
            f"<b>Overall Score:</b> {result_data['overall_score']:.0f} pts"
        ],
        [
            f"<b>Pilot:</b> {pairing_data['pilot_name']}",
            f"<b>Observer:</b> {pairing_data['observer_name']}"
        ]
    ]
    
    header_table = Table(header_table_data, colWidths=[3.5*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F0F7')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#999999')),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))
    
    # ===== COMPLETE RESULTS TABLE =====
    
    story.append(Paragraph("<b>Complete Results Summary</b>", styles['Heading3']))
    story.append(Spacer(1, 0.1*inch))
    
    # Build comprehensive table matching web UI
    table_data = [
        # Header row
        ['Leg', 'Est Time', 'Act Time', 'Dev', 'Time Pts', 'Method',
         'Off Course (NM)', 'Off Course Pts', 'Total Pts'],
    ]
    
    # Leg rows
    for i, cp in enumerate(result_data['checkpoint_results'], 1):
        est_time = f"{int(cp['estimated_time']//60):02d}:{int(cp['estimated_time']%60):02d}"
        act_time = f"{int(cp['actual_time']//60):02d}:{int(cp['actual_time']%60):02d}"
        
        within = '✓' if cp.get('within_0_25_nm') else f"{max(0, cp['distance_nm'] - 0.25):.3f} over"
        
        table_data.append([
            f"Leg {i}: {cp['name']}",
            est_time,
            act_time,
            f"{cp['deviation']:+.0f}s",
            f"{cp['leg_score']:.0f}",
            cp['method'],
            f"{cp['distance_nm']:.3f}",
            f"{cp['off_course_penalty']:.0f}",
            f"{(cp['leg_score'] + cp['off_course_penalty']):.0f}"
        ])
    
    # Total time row
    est_total = f"{int(result_data.get('estimated_total_time', 0)//60):02d}:{int(result_data.get('estimated_total_time', 0)%60):02d}"
    act_total = f"{int(result_data.get('actual_total_time', 0)//60):02d}:{int(result_data.get('actual_total_time', 0)%60):02d}"
    
    table_data.append([
        '<b>Total Time</b>',
        est_total,
        act_total,
        f"{result_data.get('total_time_deviation', 0):+.0f}s",
        f"<b>{result_data['total_time_penalty']:.0f}</b>",
        '—',
        '—',
        '—',
        f"<b>{result_data['total_time_penalty']:.0f}</b>"
    ])
    
    # Subtotal
    table_data.append([
        '<b>TIMING SUBTOTAL</b>',
        '', '', '', '',
        '', '', '',
        f"<b>{result_data['total_time_score']:.0f}</b>"
    ])
    
    # Additional penalties
    table_data.append(['', '', '', '', '', '', '', '', ''])
    table_data.append([
        '<b>Fuel Burn</b>',
        f"{result_data.get('estimated_fuel_burn', 0):.1f} gal",
        f"{result_data.get('actual_fuel_burn', 0):.1f} gal",
        f"{result_data.get('fuel_error_pct', 0):+.1f}%",
        '—', '—', '—', '—',
        f"<b>{result_data['fuel_penalty']:.0f}</b>"
    ])
    
    table_data.append([
        '<b>Checkpoint Secrets</b>',
        f"{result_data.get('secrets_missed_checkpoint', 0)}",
        '—', '—', '—', '—', '—', '—',
        f"<b>{result_data['checkpoint_secrets_penalty']:.0f}</b>"
    ])
    
    table_data.append([
        '<b>Enroute Secrets</b>',
        f"{result_data.get('secrets_missed_enroute', 0)}",
        '—', '—', '—', '—', '—', '—',
        f"<b>{result_data['enroute_secrets_penalty']:.0f}</b>"
    ])
    
    # Create results table
    results_table = Table(table_data, colWidths=[
        1.1*inch, 0.85*inch, 0.85*inch, 0.65*inch, 0.7*inch, 
        0.75*inch, 1*inch, 0.85*inch, 0.85*inch
    ])
    
    results_table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Body text
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        
        # Subtotal row styling
        ('BACKGROUND', (0, len(result_data['checkpoint_results']) + 2), 
         (-1, len(result_data['checkpoint_results']) + 2), colors.HexColor('#D0D0D0')),
        ('FONTNAME', (0, len(result_data['checkpoint_results']) + 2), 
         (-1, len(result_data['checkpoint_results']) + 2), 'Helvetica-Bold'),
    ]))
    
    story.append(results_table)
    story.append(PageBreak())
    
    # ===== MAPS SECTION =====
    
    # Full route map
    story.append(Paragraph("<b>Complete Flight Route Map</b>", styles['Heading3']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "<i>Blue dashed line: Planned route | Red solid line: Actual track</i>",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.1*inch))
    
    if full_route_map_path.exists():
        try:
            img = Image(str(full_route_map_path), width=7*inch, height=5.25*inch)
            story.append(img)
        except Exception as e:
            logger.error(f"Failed to add full route map: {e}")
    
    story.append(PageBreak())
    
    # Checkpoint detail maps
    if checkpoint_maps_paths:
        story.append(Paragraph("<b>Checkpoint Detail Maps</b>", styles['Heading3']))
        story.append(Spacer(1, 0.1*inch))
        
        for i, map_path in enumerate(checkpoint_maps_paths):
            if not map_path.exists():
                continue
            
            try:
                cp_name = result_data['checkpoint_results'][i]['name'] if i < len(result_data['checkpoint_results']) else f"CP {i+1}"
                story.append(Paragraph(f"<b>Checkpoint {i+1}: {cp_name}</b>", styles['Heading4']))
                story.append(Spacer(1, 0.05*inch))
                
                img = Image(str(map_path), width=6*inch, height=6*inch)
                story.append(img)
                
                if i < len(checkpoint_maps_paths) - 1:
                    story.append(PageBreak())
            except Exception as e:
                logger.error(f"Failed to add checkpoint {i+1} map: {e}")
    
    # Build PDF
    doc.build(story)
    logger.info(f"Enhanced PDF report saved: {output_path}")
