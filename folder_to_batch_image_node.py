import os
from typing import List, Tuple

import numpy as np
import torch
from PIL import Image, ImageOps


class FolderToBatchImage:
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "folder_path": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "输入图片文件夹路径（可选）",
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING")
    RETURN_NAMES = ("images", "count", "files")
    FUNCTION = "load"
    CATEGORY = "image/load"

    @staticmethod
    def _collect_image_paths(folder_path: str) -> List[str]:
        paths: List[str] = []
        for root, _, files in os.walk(folder_path):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in FolderToBatchImage.IMAGE_EXTENSIONS:
                    paths.append(os.path.join(root, name))
        return sorted(paths)

    @staticmethod
    def _read_image(path: str) -> torch.Tensor:
        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        array = np.asarray(image).astype(np.float32) / 255.0
        return torch.from_numpy(array)

    @staticmethod
    def _pad_to_max_size(images: List[torch.Tensor]) -> torch.Tensor:
        max_h = max(img.shape[0] for img in images)
        max_w = max(img.shape[1] for img in images)

        padded: List[torch.Tensor] = []
        for img in images:
            h, w, _ = img.shape
            if h == max_h and w == max_w:
                padded.append(img)
                continue

            canvas = torch.zeros((max_h, max_w, 3), dtype=img.dtype)
            canvas[:h, :w, :] = img
            padded.append(canvas)

        return torch.stack(padded, dim=0)

    def load(self, folder_path: str = "") -> Tuple[torch.Tensor, int, str]:
        folder_path = (folder_path or "").strip()
        if not folder_path:
            raise ValueError("folder_path 为空，请输入一个有效的文件夹路径。")

        if not os.path.isdir(folder_path):
            raise ValueError(f"folder_path 不存在或不是文件夹: {folder_path}")

        image_paths = self._collect_image_paths(folder_path)
        if not image_paths:
            raise ValueError(f"在文件夹中未找到图片: {folder_path}")

        tensors = [self._read_image(path) for path in image_paths]
        batch = self._pad_to_max_size(tensors)
        files = "\n".join(image_paths)
        return batch, len(image_paths), files
