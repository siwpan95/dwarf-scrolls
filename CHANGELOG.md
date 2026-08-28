# Changelog

本项目所有值得注意的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Fixed

- 阶段 4 勘查修复（2026-08-27）：迁仓拍平后包名 dwarf_scrolls 无法导入——新增仓库根 dwarf_scrolls.py 包名桥 + main.py/pytest.ini 路径修正，应用恢复可用（86/86 全绿）；规则内核接入判定=无同构原语不接入（README 记账）。

## [1.0.0] - 2026-08-27

### Added

- 首个发行版：Windows 可执行程序（PyInstaller，Python 3.14）。
- 发布面：gitee [siwpan/dwarf-scrolls](https://gitee.com/siwpan/dwarf-scrolls) release `v1.0.0`（矮人卷轴 v1.0.0）。