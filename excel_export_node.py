import os
from typing import List, Tuple
import ast
import json

try:
    import folder_paths
except Exception:  # pragma: no cover
    folder_paths = None


class SaveAttributesToExcel:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "length": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "width": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "height": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "material": ("STRING", {"default": ""}),
                "label": ("STRING", {"default": ""}),
            },
            "optional": {
                "output_dir": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "留空时保存到 ComfyUI outputs 目录",
                    },
                ),
                "filename_prefix": ("STRING", {"default": "attributes", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("xlsx_path", "save_hint")
    FUNCTION = "save"
    CATEGORY = "utils/export"

    @staticmethod
    def _resolve_label_value(label: str) -> str:
        if label is None:
            return ""

        if isinstance(label, (list, tuple)):
            items = [str(item).strip() for item in label if str(item).strip()]
            return items[0] if items else ""

        text = str(label).strip()
        if not text:
            return ""

        if text.startswith("[") and text.endswith("]"):
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(text)
                    if isinstance(parsed, (list, tuple)):
                        items = [str(item).strip() for item in parsed if str(item).strip()]
                        return items[0] if items else ""
                except Exception:
                    continue

        return text


    @staticmethod
    def _resolve_output_dir(output_dir: str) -> str:
        custom_dir = (output_dir or "").strip()
        if custom_dir:
            return os.path.abspath(custom_dir)

        if folder_paths is not None and hasattr(folder_paths, "get_output_directory"):
            try:
                return os.path.abspath(folder_paths.get_output_directory())
            except Exception:
                pass

        return os.path.abspath("outputs")

    @staticmethod
    def _resolve_output_path(output_dir: str, filename_prefix: str) -> str:
        safe_output_dir = SaveAttributesToExcel._resolve_output_dir(output_dir)
        os.makedirs(safe_output_dir, exist_ok=True)

        safe_prefix = (filename_prefix or "attributes").strip() or "attributes"
        return os.path.join(safe_output_dir, f"{safe_prefix}.xlsx")

    @staticmethod
    def _build_save_hint(xlsx_path: str) -> str:
        output_dir = os.path.dirname(xlsx_path)
        return f"Excel 已保存到: {xlsx_path}（目录: {output_dir}）"

    def save(
        self,
        length: float,
        width: float,
        height: float,
        material: str,
        label: str,
        output_dir: str = "",
        filename_prefix: str = "attributes",
    ) -> Tuple[str, str]:
        try:
            from openpyxl import Workbook, load_workbook
        except Exception as exc:
            raise RuntimeError(
                "需要 openpyxl 才能导出 .xlsx 文件，请在 ComfyUI 环境中安装：pip install openpyxl"
            ) from exc

        out_path = self._resolve_output_path(output_dir, filename_prefix)

        if os.path.exists(out_path):
            wb = load_workbook(out_path)
            ws = wb.active
            if ws.max_row < 1:
                ws.append(["label", "material", "length", "width", "height"])
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = "data"
            ws.append(["label", "material", "length", "width", "height"])

        label_value = self._resolve_label_value(label)
        ws.append([label_value, material, length, width, height])

        wb.save(out_path)

        save_hint = self._build_save_hint(out_path)
        print(save_hint)
        return out_path, save_hint
