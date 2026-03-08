import math
from typing import Tuple

import numpy as np

try:
    import open3d as o3d
except Exception:  # pragma: no cover
    o3d = None


class _PointCloudUtils:
    @staticmethod
    def _ensure_open3d():
        if o3d is None:
            raise RuntimeError(
                "open3d is required for these point cloud nodes. Please install open3d in the ComfyUI environment."
            )

    @staticmethod
    def to_triangle_mesh(mesh):
        _PointCloudUtils._ensure_open3d()
        if isinstance(mesh, o3d.geometry.TriangleMesh):
            return mesh

        if isinstance(mesh, dict) and "vertices" in mesh and "triangles" in mesh:
            vertices = np.asarray(mesh["vertices"], dtype=np.float64)
            triangles = np.asarray(mesh["triangles"], dtype=np.int32)
            out = o3d.geometry.TriangleMesh()
            out.vertices = o3d.utility.Vector3dVector(vertices)
            out.triangles = o3d.utility.Vector3iVector(triangles)
            return out

        raise TypeError(
            "Unsupported mesh input. Expected open3d.geometry.TriangleMesh or dict with vertices/triangles."
        )

    @staticmethod
    def to_point_cloud(point_cloud):
        _PointCloudUtils._ensure_open3d()
        if isinstance(point_cloud, o3d.geometry.PointCloud):
            return point_cloud

        if isinstance(point_cloud, np.ndarray):
            if point_cloud.ndim != 2 or point_cloud.shape[1] != 3:
                raise ValueError("Numpy point cloud must have shape (N, 3).")
            out = o3d.geometry.PointCloud()
            out.points = o3d.utility.Vector3dVector(point_cloud.astype(np.float64))
            return out

        if isinstance(point_cloud, dict) and "points" in point_cloud:
            pts = np.asarray(point_cloud["points"], dtype=np.float64)
            if pts.ndim != 2 or pts.shape[1] != 3:
                raise ValueError("point_cloud['points'] must have shape (N, 3).")
            out = o3d.geometry.PointCloud()
            out.points = o3d.utility.Vector3dVector(pts)
            return out

        raise TypeError(
            "Unsupported point cloud input. Expected open3d.geometry.PointCloud, ndarray (N,3), or dict with points."
        )


class MeshToPointCloud:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh": ("MESH",),
                "sample_points": ("INT", {"default": 20000, "min": 100, "max": 500000, "step": 100}),
                "use_poisson_disk": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("POINT_CLOUD",)
    FUNCTION = "convert"
    CATEGORY = "3d/point_cloud"

    def convert(self, mesh, sample_points: int, use_poisson_disk: bool):
        tri_mesh = _PointCloudUtils.to_triangle_mesh(mesh)
        if use_poisson_disk:
            pcd = tri_mesh.sample_points_poisson_disk(number_of_points=sample_points)
        else:
            pcd = tri_mesh.sample_points_uniformly(number_of_points=sample_points)
        return (pcd,)


class PointCloudRANSACFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "point_cloud": ("POINT_CLOUD",),
                "distance_threshold": ("FLOAT", {"default": 0.005, "min": 0.0001, "max": 10.0, "step": 0.0001}),
                "ransac_n": ("INT", {"default": 3, "min": 3, "max": 20, "step": 1}),
                "num_iterations": ("INT", {"default": 1000, "min": 10, "max": 200000, "step": 10}),
                "keep": (["outliers", "inliers"], {"default": "outliers"}),
            }
        }

    RETURN_TYPES = ("POINT_CLOUD",)
    FUNCTION = "filter"
    CATEGORY = "3d/point_cloud"

    def filter(self, point_cloud, distance_threshold: float, ransac_n: int, num_iterations: int, keep: str):
        pcd = _PointCloudUtils.to_point_cloud(point_cloud)
        if len(pcd.points) < ransac_n:
            return (pcd,)

        _, inlier_indices = pcd.segment_plane(
            distance_threshold=distance_threshold,
            ransac_n=ransac_n,
            num_iterations=num_iterations,
        )

        invert = keep == "outliers"
        filtered = pcd.select_by_index(inlier_indices, invert=invert)
        return (filtered,)


class PointCloudDBSCANLargestCluster:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "point_cloud": ("POINT_CLOUD",),
                "eps": ("FLOAT", {"default": 0.01, "min": 0.0001, "max": 10.0, "step": 0.0001}),
                "min_points": ("INT", {"default": 20, "min": 2, "max": 10000, "step": 1}),
            }
        }

    RETURN_TYPES = ("POINT_CLOUD",)
    FUNCTION = "keep_largest"
    CATEGORY = "3d/point_cloud"

    def keep_largest(self, point_cloud, eps: float, min_points: int):
        pcd = _PointCloudUtils.to_point_cloud(point_cloud)
        if len(pcd.points) == 0:
            return (pcd,)

        labels = np.asarray(pcd.cluster_dbscan(eps=eps, min_points=min_points, print_progress=False), dtype=np.int32)
        valid = labels >= 0
        if not np.any(valid):
            return (pcd,)

        counts = np.bincount(labels[valid])
        largest_label = int(np.argmax(counts))
        indices = np.where(labels == largest_label)[0].tolist()
        largest_cluster = pcd.select_by_index(indices)
        return (largest_cluster,)


class PointCloudBoundingBoxSize:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "point_cloud": ("POINT_CLOUD",),
                "oriented": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("length", "width", "height")
    FUNCTION = "measure"
    CATEGORY = "3d/point_cloud"

    @staticmethod
    def _sorted_extents(extents: np.ndarray) -> Tuple[float, float, float]:
        dims = np.sort(np.asarray(extents, dtype=np.float64))[::-1]
        return float(dims[0]), float(dims[1]), float(dims[2])

    def measure(self, point_cloud, oriented: bool):
        pcd = _PointCloudUtils.to_point_cloud(point_cloud)
        if len(pcd.points) == 0:
            return (0.0, 0.0, 0.0)

        if oriented:
            bbox = pcd.get_oriented_bounding_box()
        else:
            bbox = pcd.get_axis_aligned_bounding_box()

        length, width, height = self._sorted_extents(bbox.extent)

        if not all(math.isfinite(v) for v in (length, width, height)):
            raise RuntimeError("Computed bounding box dimensions are invalid.")

        return (length, width, height)
