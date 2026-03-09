from typing import Dict, Tuple


class FillStringUntilFull:
    """Accumulate incoming pieces until a target length is reached, then emit."""

    _buffers: Dict[str, str] = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("STRING", {"default": "", "multiline": False}),
                "target_length": ("INT", {"default": 10, "min": 1, "max": 1000000}),
            },
            "optional": {
                "number_value": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "use_number": ("BOOLEAN", {"default": False}),
                "buffer_key": ("STRING", {"default": "default", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("output", "is_ready", "status")
    FUNCTION = "append_and_output"
    CATEGORY = "utils/text"

    def append_and_output(
        self,
        value: str,
        target_length: int,
        number_value: float = 0.0,
        use_number: bool = False,
        buffer_key: str = "default",
    ) -> Tuple[str, bool, str]:
        key = (buffer_key or "default").strip() or "default"
        piece = str(number_value) if use_number else str(value)

        current = self._buffers.get(key, "")
        current += piece

        if len(current) < target_length:
            self._buffers[key] = current
            status = (
                f"缓冲中: key={key}, 当前长度={len(current)}, 目标长度={target_length}, 尚未输出"
            )
            print(status)
            return "", False, status

        output = current[:target_length]
        remainder = current[target_length:]
        self._buffers[key] = remainder

        status = (
            f"已输出: key={key}, 输出长度={len(output)}, 剩余长度={len(remainder)}, "
            f"目标长度={target_length}"
        )
        print(status)
        return output, True, status
