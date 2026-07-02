# Mizore Sorter & Nozomi Viewer

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-orange.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![Pillow](https://img.shields.io/badge/Image-Pillow-yellow.svg)](https://python-pillow.org/)

## 💡 介绍

**Mizore Sorter** 和 **Nozomi Viewer** 是一套用于本地二次元图库整理和浏览的轻量级工具。

这两个工具没有太多复杂的功能，主要目的是将含有大量图片的文件夹（例如手机里的 Twitter、Pixiv 文件夹）进行分类。目前仅支持将图片移动到自定义文件夹中这一种分类方式。

---

## ⚡ 核心功能

### ❄️ Mizore Sorter：图片分类器

- **快捷键分类**：为不同的目标文件夹绑定快捷键，通过键盘快速将图片移到目标文件夹中。
- **撤销功能**：支持通过 `Ctrl+Z` 撤销上一次的移动操作，防止手滑分错。
- **进度统计**：底部实时显示“待分类”和“已分类”的图片总数。
- **标签管理**：可视化管理分类标签，支持拖拽调整标签的显示排序。支持三种排序方式：
  1. 按照字母顺序排序
  2. 按照自定义顺序排序
  3. 按照图片数量排序
- **主题管理**：支持三种主题：Mizore、Light、Dark 和自定义字体管理，推荐 [975 Maru](https://github.com/lxgw/975Yuan) 字体的 Regular 字重。

<img width="1752" height="1101" alt="Mizore Sorter" src="https://github.com/user-attachments/assets/43701ef9-f7b0-445d-b2b6-52fade58a3f8" />


### ☂️ Nozomi Viewer：图片浏览器

注意，此浏览器功能极其不完善，仅为 **Mizore Sorter** 在未添加撤销功能时的备用方案。也可以用它二次筛选其中的图片，并且把被错放的文件移到正确的文件夹里

- **分页加载**：画廊模式下采用分批加载机制，避免大文件夹卡顿。
- **双模式切换**：支持在“画廊”和“单图”模式之间无缝切换。
- **快速纠错功能**：在看图时如果发现分错类的图片，可以通过侧边栏直接将其移动到正确的分类中，面板数据会自动更新。

<img width="1342" height="879" alt="Nozomi Viewer" src="https://github.com/user-attachments/assets/c563a65b-31e6-4709-bb93-b7047e9406a3" />


---

## 💡 开发初衷

本项目的初衷是整理发送于北宇治迫伞部的 7000 余张二次元（主要为百合）图片，并上传至群相册和官方网站。但由于图片数量过于庞大、涵盖的标签也过于丰富，若直接在手机或电脑端的原生软件和任务管理器里操作会极其不便利。因此，基于 Vibe Coding 制作了 Mizole Sorter 这一工具。键盘快捷键极大地提升了分类图片的速度。

当然，由于本人没有什么代码功底，因此写出的程序很容易出现 bug，为此我增添了很多手动刷新按钮，在出现 bug 时，可以点击这些刷新按钮，这可以解决例如标签排序不正确、图片边缘有黑框或者显示不完全等等问题。

虽然少了一些动态自适应的特性（技术不足导致的），但比较稳定。
