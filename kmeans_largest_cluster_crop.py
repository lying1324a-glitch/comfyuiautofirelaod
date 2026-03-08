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
            }
        }

    RETURN_TYPES = ("IMAGE",)
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

        labels = np.zeros(num_pixels, dtype=np.int32)
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
    def _crop_largest_cluster(image_np: np.ndarray, k: int, max_iter: int, seed: int) -> np.ndarray:
        h, w, _ = image_np.shape
        pixels = image_np.reshape(-1, 3).astype(np.float32)

        labels = KMeansLargestClusterCrop._kmeans_pixels(pixels, k, max_iter, seed).reshape(h, w)
        counts = np.bincount(labels.ravel())
        largest_label = int(np.argmax(counts))
        mask = labels == largest_label

        ys, xs = np.where(mask)
        if ys.size == 0 or xs.size == 0:
            return image_np

        y_min, y_max = ys.min(), ys.max() + 1
        x_min, x_max = xs.min(), xs.max() + 1
        return image_np[y_min:y_max, x_min:x_max, :]

    def process(self, image: torch.Tensor, k: int, max_iter: int, seed: int):
        image_np = image.detach().cpu().numpy()

        cropped_tensors = []
        max_h = 0
        max_w = 0

        for i in range(image_np.shape[0]):
            img = np.clip(image_np[i], 0.0, 1.0)
            img_u8 = (img * 255.0).astype(np.uint8)
            cropped = self._crop_largest_cluster(img_u8, k=k, max_iter=max_iter, seed=seed + i)
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
        return (output,)
