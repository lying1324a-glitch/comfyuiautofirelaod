app.registerExtension({
  name: "comfyuiautoreload.folder_to_batch_image_picker",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== "FolderToBatchImage") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

      this.addWidget("button", "选择文件夹", null, () => {
        const folderWidget = this.widgets?.find((w) => w.name === "folder_path");
        if (!folderWidget) return;

        const input = document.createElement("input");
        input.type = "file";
        input.webkitdirectory = true;
        input.multiple = true;
        input.style.display = "none";

        input.onchange = () => {
          const files = input.files;
          let selectedPath = "";

          if (files && files.length > 0) {
            const first = files[0];
            const fullPath = first.path || "";
            const relativePath = first.webkitRelativePath || "";

            if (fullPath && relativePath) {
              const fullUnix = fullPath.replace(/\\/g, "/");
              const relUnix = relativePath.replace(/\\/g, "/");
              if (fullUnix.endsWith(relUnix)) {
                selectedPath = fullUnix.slice(0, fullUnix.length - relUnix.length - 1);
              } else {
                selectedPath = fullPath;
              }
            }
          }

          if (!selectedPath) {
            const fallback = window.prompt("无法自动获取绝对路径，请手动输入文件夹路径", folderWidget.value || "");
            if (fallback === null) return;
            selectedPath = fallback;
          }

          folderWidget.value = selectedPath;
          if (typeof folderWidget.callback === "function") {
            folderWidget.callback(selectedPath, this, folderWidget);
          }
        };

        document.body.appendChild(input);
        input.click();
        setTimeout(() => input.remove(), 0);
      });

      return result;
    };
  },
});
