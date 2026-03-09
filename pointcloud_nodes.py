import math
from typing import Tuple

import numpy as np

try:
    import torch
except Exception:  # pragma: no cover
    torch = None

try:
    import open3d as o3d
except Exception:  # pragma: no cover
    o3d = None




class _ArrayTensorLike:
    """Minimal tensor-like wrapper for environments without torch."""

    def __init__(self, array):
        self._array = np.asarray(array)

    def __getitem__(self, item):
        return _ArrayTensorLike(self._array[item])

    @property
    def shape(self):
        return self._array.shape

    def cpu(self):
        return self

    def numpy(self):
        return self._array


class ComfyMeshData:
    """Mesh container compatible with ComfyUI mesh consumers.

    Expected access pattern in downstream nodes:
    `mesh.vertices[i].cpu().numpy()` and `mesh.faces[i].cpu().numpy()`.
    """

    def __init__(self, vertices: np.ndarray, faces: np.ndarray):
        v = np.asarray(vertices, dtype=np.float32)
        f = np.asarray(faces, dtype=np.int64)

        if v.ndim == 2:
            v = v[None, ...]
        if f.ndim == 2:
            f = f[None, ...]

        if torch is not None:
            self.vertices = torch.from_numpy(v)
            self.faces = torch.from_numpy(f)
        else:  # pragma: no cover
            self.vertices = _ArrayTensorLike(v)
            self.faces = _ArrayTensorLike(f)

        # alias for compatibility
        self.triangles = self.faces


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

        vertices, triangles = _PointCloudUtils._extract_mesh_components(mesh)
        if vertices is None or triangles is None:
            raise TypeError(
                "Unsupported mesh input. Expected Open3D TriangleMesh or object/dict containing vertices+faces/triangles."
            )
        return _PointCloudUtils._build_triangle_mesh(vertices, triangles)

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

        if hasattr(point_cloud, "points"):
            pts = _PointCloudUtils._to_numpy(getattr(point_cloud, "points"))
            return _PointCloudUtils._build_point_cloud(pts)

        if isinstance(point_cloud, dict) and "points" in point_cloud:
            pts = _PointCloudUtils._to_numpy(point_cloud["points"])
            return _PointCloudUtils._build_point_cloud(pts)

        if isinstance(point_cloud, dict) and "xyz" in point_cloud:
            pts = _PointCloudUtils._to_numpy(point_cloud["xyz"])
            return _PointCloudUtils._build_point_cloud(pts)

        raise TypeError(
            "Unsupported point cloud input. Expected open3d.geometry.PointCloud, ndarray (N,3), or dict with points."
        )


    @staticmethod
    def _extract_mesh_components(mesh):
        def pick_from_dict(d):
            vertex_keys = ("vertices", "verts", "v", "vertex", "pos", "positions")
            face_keys = ("triangles", "faces", "f", "indices", "face")
            vv = next((d[k] for k in vertex_keys if k in d), None)
            ff = next((d[k] for k in face_keys if k in d), None)
            if vv is not None and ff is not None:
                return vv, ff
            return None, None

        # Dict-like inputs
        if isinstance(mesh, dict):
            vv, ff = pick_from_dict(mesh)
            if vv is not None:
                return vv, ff

        # Common attribute names on custom objects
        attr_vertex_candidates = ("vertices", "verts", "v", "vertex", "positions", "pos")
        attr_face_candidates = ("triangles", "faces", "f", "indices", "face")
        vv = next((getattr(mesh, k) for k in attr_vertex_candidates if hasattr(mesh, k)), None)
        ff = next((getattr(mesh, k) for k in attr_face_candidates if hasattr(mesh, k)), None)
        if vv is not None and ff is not None:
            return vv, ff

        # Wrapped mesh containers (`mesh`, `data`, `value`, etc.)
        for wrapper_name in ("mesh", "data", "value", "payload", "obj"):
            if hasattr(mesh, wrapper_name):
                wrapped = getattr(mesh, wrapper_name)
                vv, ff = _PointCloudUtils._extract_mesh_components(wrapped)
                if vv is not None and ff is not None:
                    return vv, ff

        # Dataclass or object namespace fallback
        if hasattr(mesh, "__dict__"):
            vv, ff = pick_from_dict(vars(mesh))
            if vv is not None and ff is not None:
                return vv, ff

        return None, None

    @staticmethod
    def _to_numpy(value):
        if torch is not None and isinstance(value, torch.Tensor):
            return value.detach().cpu().numpy()
        return np.asarray(value)

    @staticmethod
    def _unwrap_batch(arr: np.ndarray, name: str) -> np.ndarray:
        arr = np.asarray(arr)
        if arr.ndim == 3 and arr.shape[0] == 1:
            return arr[0]
        if arr.ndim == 3 and arr.shape[-1] in (3, 4):
            return arr[0]
        if arr.ndim == 2:
            return arr
        raise ValueError(f"{name} should be shape (N, C) or (1, N, C), got {arr.shape}.")

    @staticmethod
    def _build_triangle_mesh(vertices, triangles):
        vertices = _PointCloudUtils._unwrap_batch(_PointCloudUtils._to_numpy(vertices), "vertices")
        triangles = _PointCloudUtils._unwrap_batch(_PointCloudUtils._to_numpy(triangles), "triangles")

        if vertices.shape[1] > 3:
            vertices = vertices[:, :3]
        if triangles.shape[1] > 3:
            triangles = triangles[:, :3]

        if vertices.shape[1] != 3:
            raise ValueError(f"Mesh vertices must have 3 columns, got {vertices.shape}.")
        if triangles.shape[1] != 3:
            raise ValueError(f"Mesh triangles/faces must have 3 columns, got {triangles.shape}.")

        out = o3d.geometry.TriangleMesh()
        out.vertices = o3d.utility.Vector3dVector(vertices.astype(np.float64))
        out.triangles = o3d.utility.Vector3iVector(triangles.astype(np.int32))
        return out

    @staticmethod
    def _build_point_cloud(points):
        points = _PointCloudUtils._unwrap_batch(_PointCloudUtils._to_numpy(points), "points")
        if points.shape[1] > 3:
            points = points[:, :3]
        if points.shape[1] != 3:
            raise ValueError(f"Point cloud points must have 3 columns, got {points.shape}.")

        out = o3d.geometry.PointCloud()
        out.points = o3d.utility.Vector3dVector(points.astype(np.float64))
        return out


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

    @staticmethod
    def _is_empty_mesh(tri_mesh) -> bool:
        # Some mesh objects (including non-open3d wrappers) do not expose `is_empty`.
        if hasattr(tri_mesh, "is_empty") and callable(getattr(tri_mesh, "is_empty")):
            try:
                return bool(tri_mesh.is_empty())
            except Exception:
                pass

        vertices = np.asarray(tri_mesh.vertices)
        triangles = np.asarray(tri_mesh.triangles)
        return vertices.shape[0] == 0 or triangles.shape[0] == 0

    def convert(self, mesh, sample_points: int, use_poisson_disk: bool):
        tri_mesh = _PointCloudUtils.to_triangle_mesh(mesh)
        if self._is_empty_mesh(tri_mesh):
            raise ValueError("Input mesh is empty (no vertices or no triangles), cannot sample point cloud.")

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




class PointCloudLargestSurfaceAfterAxisPlaneFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "point_cloud": ("POINT_CLOUD",),
                "plane_distance_threshold": ("FLOAT", {"default": 0.003, "min": 0.0001, "max": 1.0, "step": 0.0001}),
                "axis_angle_threshold_deg": ("FLOAT", {"default": 10.0, "min": 1.0, "max": 45.0, "step": 0.5}),
                "min_plane_points": ("INT", {"default": 200, "min": 20, "max": 200000, "step": 10}),
                "max_plane_iterations": ("INT", {"default": 8, "min": 1, "max": 64, "step": 1}),
                "cluster_eps": ("FLOAT", {"default": 0.01, "min": 0.0001, "max": 10.0, "step": 0.0001}),
                "cluster_min_points": ("INT", {"default": 30, "min": 2, "max": 10000, "step": 1}),
            }
        }

    RETURN_TYPES = ("POINT_CLOUD",)
    FUNCTION = "filter"
    CATEGORY = "3d/point_cloud"

    @staticmethod
    def _is_axis_aligned_plane(normal: np.ndarray, angle_threshold_deg: float) -> bool:
        n = np.asarray(normal, dtype=np.float64)
        norm = np.linalg.norm(n)
        if norm <= 1e-12:
            return False
        n = n / norm

        axes = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)
        cos_angle = np.max(np.abs(axes @ n))
        cos_threshold = math.cos(math.radians(angle_threshold_deg))
        return cos_angle >= cos_threshold

    @staticmethod
    def _surface_area_score(cluster_pcd):
        if len(cluster_pcd.points) < 4:
            return 0.0
        try:
            hull, _ = cluster_pcd.compute_convex_hull()
            area = float(hull.get_surface_area())
            if math.isfinite(area):
                return area
        except Exception:
            pass

        bbox = cluster_pcd.get_oriented_bounding_box()
        ex = np.asarray(bbox.extent, dtype=np.float64)
        if ex.shape[0] != 3:
            return 0.0
        l, w, h = ex
        return float(max(0.0, 2.0 * (l * w + w * h + h * l)))

    def _remove_axis_aligned_planes(
        self,
        pcd,
        plane_distance_threshold: float,
        axis_angle_threshold_deg: float,
        min_plane_points: int,
        max_plane_iterations: int,
    ):
        working = pcd
        for _ in range(max_plane_iterations):
            if len(working.points) < max(3, min_plane_points):
                break

            model, inliers = working.segment_plane(
                distance_threshold=plane_distance_threshold,
                ransac_n=3,
                num_iterations=1000,
            )
            inliers = list(inliers)
            if len(inliers) < min_plane_points:
                break

            normal = np.asarray(model[:3], dtype=np.float64)
            if self._is_axis_aligned_plane(normal, axis_angle_threshold_deg):
                working = working.select_by_index(inliers, invert=True)
            else:
                break
        return working

    def filter(
        self,
        point_cloud,
        plane_distance_threshold: float,
        axis_angle_threshold_deg: float,
        min_plane_points: int,
        max_plane_iterations: int,
        cluster_eps: float,
        cluster_min_points: int,
    ):
        pcd = _PointCloudUtils.to_point_cloud(point_cloud)
        if len(pcd.points) == 0:
            return (pcd,)

        no_planes = self._remove_axis_aligned_planes(
            pcd,
            plane_distance_threshold=plane_distance_threshold,
            axis_angle_threshold_deg=axis_angle_threshold_deg,
            min_plane_points=min_plane_points,
            max_plane_iterations=max_plane_iterations,
        )
        if len(no_planes.points) == 0:
            return (no_planes,)

        labels = np.asarray(
            no_planes.cluster_dbscan(eps=cluster_eps, min_points=cluster_min_points, print_progress=False),
            dtype=np.int32,
        )
        valid = labels >= 0
        if not np.any(valid):
            return (no_planes,)

        best_label = None
        best_area = -1.0
        for label in np.unique(labels[valid]):
            indices = np.where(labels == label)[0].tolist()
            cluster = no_planes.select_by_index(indices)
            area = self._surface_area_score(cluster)
            if area > best_area:
                best_area = area
                best_label = int(label)

        if best_label is None:
            return (no_planes,)

        keep_indices = np.where(labels == best_label)[0].tolist()
        return (no_planes.select_by_index(keep_indices),)


class PointCloudToMesh:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "point_cloud": ("POINT_CLOUD",),
                "method": (["poisson", "ball_pivoting"], {"default": "poisson"}),
                "poisson_depth": ("INT", {"default": 8, "min": 5, "max": 12, "step": 1}),
                "poisson_density_quantile": ("FLOAT", {"default": 0.02, "min": 0.0, "max": 0.5, "step": 0.001}),
                "ball_radius": ("FLOAT", {"default": 0.01, "min": 0.0001, "max": 10.0, "step": 0.0001}),
                "ball_radius_scale_2": ("FLOAT", {"default": 2.0, "min": 1.0, "max": 5.0, "step": 0.1}),
                "ball_radius_scale_3": ("FLOAT", {"default": 4.0, "min": 1.0, "max": 10.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("MESH",)
    FUNCTION = "convert"
    CATEGORY = "3d/point_cloud"

    @staticmethod
    def _ensure_normals(pcd):
        if not pcd.has_normals():
            pcd.estimate_normals()
        pcd.normalize_normals()

    def convert(
        self,
        point_cloud,
        method: str,
        poisson_depth: int,
        poisson_density_quantile: float,
        ball_radius: float,
        ball_radius_scale_2: float,
        ball_radius_scale_3: float,
    ):
        _PointCloudUtils._ensure_open3d()
        pcd = _PointCloudUtils.to_point_cloud(point_cloud)

        if len(pcd.points) < 10:
            raise ValueError("Point cloud has too few points to reconstruct mesh (need at least 10).")

        self._ensure_normals(pcd)

        if method == "poisson":
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                pcd,
                depth=poisson_depth,
            )
            if poisson_density_quantile > 0.0:
                d = np.asarray(densities)
                threshold = np.quantile(d, poisson_density_quantile)
                keep = np.where(d >= threshold)[0]
                mesh = mesh.select_by_index(keep.tolist())
        else:
            radii = o3d.utility.DoubleVector(
                [
                    ball_radius,
                    ball_radius * ball_radius_scale_2,
                    ball_radius * ball_radius_scale_3,
                ]
            )
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, radii)

        mesh.remove_duplicated_vertices()
        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_triangles()
        mesh.remove_non_manifold_edges()

        if len(mesh.vertices) == 0 or len(mesh.triangles) == 0:
            raise ValueError("Failed to reconstruct a valid mesh from the point cloud.")

        vertices = np.asarray(mesh.vertices, dtype=np.float32)
        faces = np.asarray(mesh.triangles, dtype=np.int32)
        return (ComfyMeshData(vertices=vertices, faces=faces),)


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
