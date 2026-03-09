import importlib

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _register_node(module_name: str, class_name: str, display_name: str):
    try:
        module = importlib.import_module(f".{module_name}", package=__name__)
        node_cls = getattr(module, class_name)
    except Exception as exc:
        print(f"[comfyuiautofirelaod] Skip node {class_name}: {exc}")
        return

    NODE_CLASS_MAPPINGS[class_name] = node_cls
    NODE_DISPLAY_NAME_MAPPINGS[class_name] = display_name


_register_node("kmeans_largest_cluster_crop", "KMeansLargestClusterCrop", "KMeans Largest Cluster Crop")
_register_node("pointcloud_nodes", "MeshToPointCloud", "Mesh To Point Cloud")
_register_node("pointcloud_nodes", "PointCloudRANSACFilter", "Point Cloud RANSAC Filter")
_register_node(
    "pointcloud_nodes",
    "PointCloudDBSCANLargestCluster",
    "Point Cloud DBSCAN Largest Cluster",
)
_register_node("pointcloud_nodes", "PointCloudBoundingBoxSize", "Point Cloud Bounding Box Size")
_register_node("pointcloud_nodes", "PointCloudToMesh", "Point Cloud To Mesh")
_register_node(
    "pointcloud_nodes",
    "PointCloudLargestSurfaceAfterAxisPlaneFilter",
    "Point Cloud Largest Surface After Axis Plane Filter",
)
_register_node("folder_to_batch_image_node", "FolderToBatchImage", "Folder To Batch Image")
_register_node("excel_export_node", "SaveAttributesToExcel", "Save Attributes To Excel")
_register_node("string_buffer_node", "FillStringUntilFull", "Fill String Until Full")
