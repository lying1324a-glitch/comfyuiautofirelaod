from typing import Optional, Tuple


class StringIndexValue:
    """Split comma-separated text and return the item at the given index."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("STRING", {"default": "", "multiline": False}),
                "index": ("INT", {"default": 0, "min": -1000000, "max": 1000000}),
            },
            "optional": {
                "index_input": ("INT", {"default": 0, "min": -1000000, "max": 1000000}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("output", "is_valid", "status")
    FUNCTION = "get_value_by_index"
    CATEGORY = "utils/text"

    def get_value_by_index(
        self,
        value: str,
        index: int,
        index_input: Optional[int] = None,
    ) -> Tuple[str, bool, str]:
        text = str(value).strip()
        actual_index = index_input if index_input is not None else index

        if len(text) == 0:
            status = "输入字符串为空，无法取索引值"
            print(status)
            return "", False, status

        items = [item.strip() for item in text.split(",")]

        if actual_index < -len(items) or actual_index >= len(items):
            status = (
                f"索引越界: index={actual_index}, 分割后数量={len(items)}，"
                f"合法范围=[{-len(items)}, {len(items) - 1}]"
            )
            print(status)
            return "", False, status

        output = items[actual_index]
        status = f"取值成功: index={actual_index}, output={output}"
        print(status)
        return output, True, status
