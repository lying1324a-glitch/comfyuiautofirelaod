import numpy as np
import torch


class KMeansLargestClusterCrop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "k": ("INT", {"default": 4, "min": 2, "max": 16, "step": 1}),
                "max_iter": ("INT", {"default": 20, "min": 1, "max": 200, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**31 - 1, "step": 1}),
                "min_crop_ratio": (
                    "FLOAT",
                    {"default": 0.98, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "info")
    FUNCTION = "process"
    CATEGORY = "image/segmentation"

    @staticmethod
    def _kmeans_pixels(pixels: np.ndarray, k: int, max_iter: int, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        num_pixels = pixels.shape[0]

        if num_pixels < k:
            k = max(1, num_pixels)

        init_idx = rng.choice(num_pixels, size=k, replace=False)
        centers = pixels[init_idx].astype(np.float32)

        labels = np.full(num_pixels, -1, dtype=np.int32)
        for _ in range(max_iter):
            distances = ((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
            new_labels = np.argmin(distances, axis=1).astype(np.int32)

            if np.array_equal(new_labels, labels):
                break
            labels = new_labels

            for c in range(k):
                cluster_points = pixels[labels == c]
                if cluster_points.size == 0:
                    centers[c] = pixels[rng.integers(0, num_pixels)]
                else:
                    centers[c] = cluster_points.mean(axis=0)

        return labels

    @staticmethod
    def _largest_connected_component(mask: np.ndarray) -> np.ndarray:
        h, w = mask.shape
        visited = np.zeros((h, w), dtype=np.uint8)
        best_component = []

        for y in range(h):
            for x in range(w):
                if not mask[y, x] or visited[y, x]:
                    continue

                stack = [(y, x)]
                visited[y, x] = 1
                component = []

                while stack:
                    cy, cx = stack.pop()
                    component.append((cy, cx))

                    if cy > 0 and mask[cy - 1, cx] and not visited[cy - 1, cx]:
                        visited[cy - 1, cx] = 1
                        stack.append((cy - 1, cx))
                    if cy + 1 < h and mask[cy + 1, cx] and not visited[cy + 1, cx]:
                        visited[cy + 1, cx] = 1
                        stack.append((cy + 1, cx))
                    if cx > 0 and mask[cy, cx - 1] and not visited[cy, cx - 1]:
                        visited[cy, cx - 1] = 1
                        stack.append((cy, cx - 1))
                    if cx + 1 < w and mask[cy, cx + 1] and not visited[cy, cx + 1]:
                        visited[cy, cx + 1] = 1
                        stack.append((cy, cx + 1))

                if len(component) > len(best_component):
                    best_component = component

        out_mask = np.zeros_like(mask, dtype=bool)
        if best_component:
            ys, xs = zip(*best_component)
            out_mask[np.array(ys), np.array(xs)] = True
        return out_mask

    @staticmethod
    def _crop_largest_cluster(image_np: np.ndarray, k: int, max_iter: int, seed: int):
        h, w, _ = image_np.shape
        pixels = image_np.reshape(-1, 3).astype(np.float32)

        labels = KMeansLargestClusterCrop._kmeans_pixels(pixels, k, max_iter, seed).reshape(h, w)
        counts = np.bincount(labels.ravel())
        largest_label = int(np.argmax(counts))
        cluster_mask = labels == largest_label
        mask = KMeansLargestClusterCrop._largest_connected_component(cluster_mask)

        ys, xs = np.where(mask)
        if ys.size == 0 or xs.size == 0:
            return image_np, (0, h, 0, w)

        y_min, y_max = ys.min(), ys.max() + 1
        x_min, x_max = xs.min(), xs.max() + 1
        return image_np[y_min:y_max, x_min:x_max, :], (y_min, y_max, x_min, x_max)

    def process(self, image: torch.Tensor, k: int, max_iter: int, seed: int, min_crop_ratio: float):
        image_np = image.detach().cpu().numpy()

        cropped_tensors = []
        max_h = 0
        max_w = 0
        messages = []

        for i in range(image_np.shape[0]):
            img = np.clip(image_np[i], 0.0, 1.0)
            img_u8 = (img * 255.0).astype(np.uint8)
            cropped, bbox = self._crop_largest_cluster(img_u8, k=k, max_iter=max_iter, seed=seed + i)
            y_min, y_max, x_min, x_max = bbox
            crop_h = y_max - y_min
            crop_w = x_max - x_min
            orig_h, orig_w = img_u8.shape[0], img_u8.shape[1]
            area_ratio = (crop_h * crop_w) / float(orig_h * orig_w)

            if area_ratio >= min_crop_ratio:
                messages.append(
                    f"frame {i}: 未明显裁切（裁切面积占比 {area_ratio:.3f}），可尝试增大 k 或减小 min_crop_ratio"
                )
            else:
                messages.append(
                    f"frame {i}: 已裁切 bbox=({x_min},{y_min})-({x_max},{y_max}), 面积占比 {area_ratio:.3f}"
                )

            cropped_f = torch.from_numpy(cropped.astype(np.float32) / 255.0)
            cropped_tensors.append(cropped_f)
            max_h = max(max_h, cropped_f.shape[0])
            max_w = max(max_w, cropped_f.shape[1])

        padded = []
        for tensor in cropped_tensors:
            h, w, _ = tensor.shape
            if h == max_h and w == max_w:
                padded.append(tensor)
                continue

            canvas = torch.zeros((max_h, max_w, 3), dtype=tensor.dtype)
            canvas[:h, :w, :] = tensor
            padded.append(canvas)

        output = torch.stack(padded, dim=0)
        info = "\n".join(messages)
        return (output, info)
