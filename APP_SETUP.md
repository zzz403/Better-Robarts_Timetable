# 创建 macOS 应用的方法

你现在有3种方法将 UofT Study Rooms 变成 macOS 应用：

## 方法1: 使用 PyInstaller (推荐)

### 步骤：
1. 确保安装了所有依赖：
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. 运行构建脚本：
   ```bash
   ./build_app.sh
   ```

3. 应用会被创建在 `dist/UofT Study Rooms.app`

4. 复制到应用程序文件夹：
   ```bash
   cp -r "dist/UofT Study Rooms.app" /Applications/
   ```

## 方法2: 使用 AppleScript

### 步骤：
1. 打开 "脚本编辑器" (Script Editor)
2. 打开 `UofT_Study_Rooms.applescript` 文件
3. 选择 "文件" > "导出"
4. 选择文件格式为 "应用程序"
5. 保存为 "UofT Study Rooms.app"

## 方法3: 直接运行启动器

### 步骤：
1. 直接运行启动器：
   ```bash
   python3 launcher.py
   ```

2. 或者创建一个 Shell 脚本快捷方式

## 使用说明

创建应用后：
1. 双击应用图标启动
2. 应用会自动打开浏览器
3. 在侧边栏点击 "Get Latest Data" 获取数据
4. 点击绿色时间槽直接预约

## 注意事项

- 应用需要网络连接来获取最新数据
- 首次运行可能需要几分钟来获取所有房间数据
- 可以将应用复制到 `/Applications` 文件夹方便访问

## 故障排除

如果遇到问题：
1. 确保 Python 3 已安装
2. 确保所有依赖已安装 (`pip install -r requirements.txt`)
3. 检查网络连接
4. 查看终端输出的错误信息