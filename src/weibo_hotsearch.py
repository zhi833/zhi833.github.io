import os
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote

class WeiboHotSearch:
    def __init__(self):
        self.base_path = Path("./files/weibo")
        self.hot_search_api = "https://weibo.com/ajax/side/hotSearch"

        # 初始化目录
        self.base_path.mkdir(parents=True, exist_ok=True)

    def fetch_hot_search(self) -> List[Dict[str, Any]]:
        """获取微博热搜原始数据"""
        try:
            response = requests.get(
                self.hot_search_api,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Cookie": "你的 Cookie（如果需要）"
                },
                timeout=10
            )
            if response.status_code == 200:
                return self.process_raw_data(response.json())
        except Exception as e:
            print(f"请求失败: {str(e)}")
        return []

    def process_raw_data(self, raw_data: Dict) -> List[Dict[str, Any]]:
        """处理原始数据（对应 Java 的 revisedResult 方法）"""
        processed = []
        if raw_data.get("ok") == 1 and "data" in raw_data:
            for item in raw_data["data"]["realtime"]:
                if "realpos" in item:  # 过滤广告内容
                    processed.append({
                        "realpos": item["realpos"],
                        "word": item["word"],
                        "num": item["num"]
                    })
        return processed

    def merge_data(self, new_data: List[Dict], date_str: str) -> List[Dict]:
        """合并新旧数据（对应 hotSearchSummary 逻辑）"""
        # 读取历史数据
        history_file = self.base_path / "history.json"
        history = []
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f).get(date_str, [])

        # 合并去重逻辑
        merged = {item["word"]: item for item in history}
        for item in new_data:
            existing = merged.get(item["word"])
            if not existing or int(item["num"]) > int(existing["num"]):
                merged[item["word"]] = item

        # 排序并取前50
        sorted_data = sorted(
            merged.values(),
            key=lambda x: int(x["num"]),
            reverse=True
        )[:50]

        # 更新排名
        for idx, item in enumerate(sorted_data, 1):
            item["realpos"] = idx

        return sorted_data

    def save_data(self, data: List[Dict], date_str: str) -> None:
        """保存数据到历史文件"""
        history_file = self.base_path / "history.json"
        all_data = {}
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        all_data[date_str] = data

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False)

    def generate_markdown(self, data: List[Dict]) -> Path:
        """生成 Markdown 文件（对应 hotSearchFile 方法）"""
        now = datetime.now()
        file_path = self.base_path / f"{now:%Y}" / f"{now:%m}"
        file_path.mkdir(parents=True, exist_ok=True)

        content = [
            "# 微博热搜榜\n",
            f"**更新时间**: {now:%Y-%m-%d %H:%M}\n",
            "---\n",
            "| 排名 | 热搜词 | 热度 |",
            "|------|--------|------|"
        ]

        for idx, item in enumerate(data, 1):
            encoded_word = quote(item["word"])
            row = (
                f"| {idx} | "
                f"[{item['word']}](https://s.weibo.com/weibo?q={encoded_word}) | "
                f"{self.format_num(item['num'])} |"
            )
            content.append(row)

        output_file = file_path / f"微博热搜-{now:%Y%m%d}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        return output_file

    @staticmethod
    def format_num(num: str) -> str:
        """格式化数字显示（对应 digital 方法）"""
        n = int(num)
        if n >= 100000:
            return f"{n/10000:.1f}万"
        return str(n)

    def daily_task(self) -> None:
        """每日定时任务"""
        # 1. 获取数据
        raw_data = self.fetch_hot_search()
        if not raw_data:
            return

        # 2. 处理数据
        date_str = datetime.now().strftime("%Y-%m-%d")
        merged_data = self.merge_data(raw_data, date_str)

        # 3. 保存数据
        self.save_data(merged_data, date_str)

        # 4. 生成文件
        md_path = self.generate_markdown(merged_data)
        print(f"Markdown 文件已生成：{md_path}")

        # 5. 自动提交到 GitHub（可选）
        self.git_auto_commit()

    def git_auto_commit(self) -> None:
        """自动 Git 提交（需要配置 GitHub Actions）"""
        os.system("git add .")
        os.system(f'git commit -m "Auto update {datetime.now():%Y-%m-%d %H:%M}"')
        os.system("git push origin main")

if __name__ == "__main__":
    service = WeiboHotSearch()
    service.daily_task()
