"""
Detects planes in point clouds using RANSAC and returns colored point cloud.
"""

import numpy as np
import open3d as o3d
from typing import List, Tuple


def detect_planes_colored(pointcloud: o3d.geometry.PointCloud, 
                         max_planes: int = 5,
                         distance_threshold: float = 0.02,
                         min_plane_size: int = 100) -> o3d.geometry.PointCloud:
    """
    Detect planes in point cloud and return colored point cloud.
    
    Args:
        pointcloud: Input point cloud
        max_planes: Maximum number of planes to detect
        distance_threshold: RANSAC distance threshold
        min_plane_size: Minimum points per plane
        
    Returns:
        Colored point cloud with each plane in different color
    """
    # Predefined colors for planes
    colors = [
        [1.0, 0.0, 0.0],  # Red
        [0.0, 1.0, 0.0],  # Green  
        [0.0, 0.0, 1.0],  # Blue
        [1.0, 1.0, 0.0],  # Yellow
        [1.0, 0.0, 1.0],  # Magenta
        [0.0, 1.0, 1.0],  # Cyan
        [1.0, 0.5, 0.0],  # Orange
        [0.5, 0.0, 1.0],  # Purple
    ]
    
    # Initialize colors array (gray for non-plane points)
    point_colors = np.full((len(pointcloud.points), 3), [0.5, 0.5, 0.5])
    
    # Keep track of which points have been assigned to planes
    assigned_points = np.zeros(len(pointcloud.points), dtype=bool)
    plane_count = 0
    
    for i in range(max_planes):
        # Get unassigned points
        unassigned_indices = np.where(~assigned_points)[0]
        
        if len(unassigned_indices) < min_plane_size:
            break
            
        # Create point cloud with only unassigned points
        remaining_pcd = pointcloud.select_by_index(unassigned_indices)
        
        # Detect single plane
        plane_model, inliers = remaining_pcd.segment_plane(
            distance_threshold=distance_threshold,
            ransac_n=3,
            num_iterations=1000
        )
        
        if len(inliers) >= min_plane_size:
            # Map inliers back to original point cloud indices
            original_inlier_indices = unassigned_indices[inliers]
            
            # Color the plane points
            if plane_count < len(colors):
                point_colors[original_inlier_indices] = colors[plane_count]
                assigned_points[original_inlier_indices] = True
                plane_count += 1
        else:
            break
    
    # Create colored point cloud
    colored_pcd = o3d.geometry.PointCloud()
    colored_pcd.points = pointcloud.points
    colored_pcd.colors = o3d.utility.Vector3dVector(point_colors)
    
    return colored_pcd


def detect_planes_simple(pointcloud: o3d.geometry.PointCloud, 
                        max_planes: int = 5,
                        distance_threshold: float = 0.02) -> List[Tuple[List[float], List[int]]]:
    """
    Simple plane detection returning plane models and inlier indices.
    
    Args:
        pointcloud: Input point cloud
        max_planes: Maximum number of planes to detect
        distance_threshold: RANSAC distance threshold
        
    Returns:
        List of (plane_model, inliers) tuples
    """
    planes = []
    remaining_pcd = pointcloud
    
    for i in range(max_planes):
        if len(remaining_pcd.points) < 100:
            break
            
        plane_model, inliers = remaining_pcd.segment_plane(
            distance_threshold=distance_threshold,
            ransac_n=3,
            num_iterations=1000
        )
        
        if len(inliers) >= 100:
            planes.append((plane_model, inliers))
            remaining_pcd = remaining_pcd.select_by_index(inliers, invert=True)
        else:
            break
    
    return planes


def detect_planes_robust(pointcloud: o3d.geometry.PointCloud, 
                        max_planes: int = 5,
                        distance_threshold: float = None,
                        min_plane_size: int = 100,
                        preprocess: bool = True) -> o3d.geometry.PointCloud:
    """
    Robust plane detection with preprocessing and adaptive parameters.
    
    Args:
        pointcloud: Input point cloud
        max_planes: Maximum number of planes to detect
        distance_threshold: RANSAC distance threshold (auto-calculated if None)
        min_plane_size: Minimum points per plane
        preprocess: Whether to apply preprocessing steps
        
    Returns:
        Colored point cloud with each plane in different color
    """
    colors = [
        [1.0, 0.0, 0.0],  # Red
        [0.0, 1.0, 0.0],  # Green  
        [0.0, 0.0, 1.0],  # Blue
        [1.0, 1.0, 0.0],  # Yellow
        [1.0, 0.0, 1.0],  # Magenta
        [0.0, 1.0, 1.0],  # Cyan
        [1.0, 0.5, 0.0],  # Orange
        [0.5, 0.0, 1.0],  # Purple
    ]
    
    # Work with a copy to avoid modifying original
    pcd = pointcloud
    
    if preprocess:
        # Remove statistical outliers
        pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
        
        # Voxel downsampling to reduce noise
        voxel_size = 0.01  # Adjust based on your point cloud scale
        pcd = pcd.voxel_down_sample(voxel_size)
    
    # Auto-calculate distance threshold if not provided
    if distance_threshold is None:
        # Calculate point cloud scale
        points = np.asarray(pcd.points)
        if len(points) > 0:
            # Use 1% of the point cloud's bounding box diagonal as threshold
            bbox = pcd.get_axis_aligned_bounding_box()
            diagonal = np.linalg.norm(bbox.max_bound - bbox.min_bound)
            distance_threshold = diagonal * 0.01
        else:
            distance_threshold = 0.02
    
    # Initialize colors array (gray for non-plane points)
    point_colors = np.full((len(pcd.points), 3), [0.5, 0.5, 0.5])
    
    # Keep track of which points have been assigned to planes
    assigned_points = np.zeros(len(pcd.points), dtype=bool)
    plane_count = 0
    
    for i in range(max_planes):
        # Get unassigned points
        unassigned_indices = np.where(~assigned_points)[0]
        if len(unassigned_indices) < min_plane_size:
            break
            
        # Create point cloud with only unassigned points
        remaining_pcd = pcd.select_by_index(unassigned_indices)
        
        # Detect single plane with adaptive iterations
        num_iterations = min(2000, max(500, len(remaining_pcd.points) // 10))
        plane_model, inliers = remaining_pcd.segment_plane(
            distance_threshold=distance_threshold,
            ransac_n=3,
            num_iterations=num_iterations
        )
        
        if len(inliers) >= min_plane_size:
            # Map inliers back to original point cloud indices
            original_inlier_indices = unassigned_indices[inliers]
            
            # Color the plane points
            if plane_count < len(colors):
                point_colors[original_inlier_indices] = colors[plane_count]
                assigned_points[original_inlier_indices] = True
                plane_count += 1
                
        else:
            break
    
    # Create colored point cloud
    colored_pcd = o3d.geometry.PointCloud()
    colored_pcd.points = pcd.points
    colored_pcd.colors = o3d.utility.Vector3dVector(point_colors)
    
    return colored_pcd


def detect_planes_adaptive(pointcloud: o3d.geometry.PointCloud, 
                          max_planes: int = 5,
                          min_plane_size: int = 100) -> o3d.geometry.PointCloud:
    """
    Adaptive plane detection that tries different distance thresholds.
    
    Args:
        pointcloud: Input point cloud
        max_planes: Maximum number of planes to detect
        min_plane_size: Minimum points per plane
        
    Returns:
        Colored point cloud with each plane in different color
    """
    # Calculate point cloud scale
    points = np.asarray(pointcloud.points)
    if len(points) == 0:
        return pointcloud
    
    bbox = pointcloud.get_axis_aligned_bounding_box()
    diagonal = np.linalg.norm(bbox.max_bound - bbox.min_bound)
    
    print(f"Point cloud diagonal: {diagonal:.4f}")
    print(f"Point cloud size: {len(points)} points")
    
    # Try different distance thresholds
    thresholds = [
        diagonal * 0.005,  # 0.5% of diagonal
        diagonal * 0.01,   # 1% of diagonal
        diagonal * 0.02,   # 2% of diagonal
        diagonal * 0.05,   # 5% of diagonal
        0.01,              # Fixed small threshold
        0.02,              # Fixed medium threshold
        0.05,              # Fixed large threshold
    ]
    
    best_result = None
    best_plane_count = 0
    
    for threshold in thresholds:
        print(f"\nTrying distance threshold: {threshold:.4f}")
        result = detect_planes_colored(pointcloud, max_planes, threshold, min_plane_size)
        
        # Count how many different colors are used (excluding gray)
        colors = np.asarray(result.colors)
        unique_colors = np.unique(colors, axis=0)
        # Remove gray color [0.5, 0.5, 0.5]
        non_gray_colors = unique_colors[~np.all(unique_colors == [0.5, 0.5, 0.5], axis=1)]
        plane_count = len(non_gray_colors)
        
        print(f"Found {plane_count} planes with threshold {threshold:.4f}")
        
        if plane_count > best_plane_count:
            best_plane_count = plane_count
            best_result = result
            print(f"New best result: {plane_count} planes")
    
    if best_result is not None:
        print(f"\nBest result: {best_plane_count} planes detected")
        return best_result
    else:
        print("No planes detected with any threshold")
        return pointcloud
