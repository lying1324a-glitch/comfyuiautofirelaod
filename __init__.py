from .kmeans_largest_cluster_crop import KMeansLargestClusterCrop
from .folder_to_batch_image_node import FolderToBatchImage
from .excel_export_node import SaveAttributesToExcel
from .string_buffer_node import FillStringUntilFull
from .pointcloud_nodes import (
    MeshToPointCloud,
    PointCloudBoundingBoxSize,
    PointCloudDBSCANLargestCluster,
    PointCloudRANSACFilter,
    PointCloudToMesh,
    PointCloudLargestSurfaceAfterAxisPlaneFilter,
)

NODE_CLASS_MAPPINGS = {
    "KMeansLargestClusterCrop": KMeansLargestClusterCrop,
    "MeshToPointCloud": MeshToPointCloud,
    "PointCloudRANSACFilter": PointCloudRANSACFilter,
    "PointCloudDBSCANLargestCluster": PointCloudDBSCANLargestCluster,
    "PointCloudBoundingBoxSize": PointCloudBoundingBoxSize,
    "PointCloudToMesh": PointCloudToMesh,
    "PointCloudLargestSurfaceAfterAxisPlaneFilter": PointCloudLargestSurfaceAfterAxisPlaneFilter,
    "FolderToBatchImage": FolderToBatchImage,
    "SaveAttributesToExcel": SaveAttributesToExcel,
    "FillStringUntilFull": FillStringUntilFull,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KMeansLargestClusterCrop": "KMeans Largest Cluster Crop",
    "MeshToPointCloud": "Mesh To Point Cloud",
    "PointCloudRANSACFilter": "Point Cloud RANSAC Filter",
    "PointCloudDBSCANLargestCluster": "Point Cloud DBSCAN Largest Cluster",
    "PointCloudBoundingBoxSize": "Point Cloud Bounding Box Size",
    "PointCloudToMesh": "Point Cloud To Mesh",
    "PointCloudLargestSurfaceAfterAxisPlaneFilter": "Point Cloud Largest Surface After Axis Plane Filter",
    "FolderToBatchImage": "Folder To Batch Image",
    "SaveAttributesToExcel": "Save Attributes To Excel",
    "FillStringUntilFull": "Fill String Until Full",
}
