from .kmeans_largest_cluster_crop import KMeansLargestClusterCrop
from .pointcloud_nodes import (
    MeshToPointCloud,
    PointCloudBoundingBoxSize,
    PointCloudDBSCANLargestCluster,
    PointCloudRANSACFilter,
)

NODE_CLASS_MAPPINGS = {
    "KMeansLargestClusterCrop": KMeansLargestClusterCrop,
    "MeshToPointCloud": MeshToPointCloud,
    "PointCloudRANSACFilter": PointCloudRANSACFilter,
    "PointCloudDBSCANLargestCluster": PointCloudDBSCANLargestCluster,
    "PointCloudBoundingBoxSize": PointCloudBoundingBoxSize,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KMeansLargestClusterCrop": "KMeans Largest Cluster Crop",
    "MeshToPointCloud": "Mesh To Point Cloud",
    "PointCloudRANSACFilter": "Point Cloud RANSAC Filter",
    "PointCloudDBSCANLargestCluster": "Point Cloud DBSCAN Largest Cluster",
    "PointCloudBoundingBoxSize": "Point Cloud Bounding Box Size",
}
