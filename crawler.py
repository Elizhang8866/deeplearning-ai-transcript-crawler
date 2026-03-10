"""
DeepLearning.AI Agent Skills 课程 Transcript 爬虫
爬取课程所有课时的视频字幕并整理到 Markdown 文件
"""

import asyncio
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser


@dataclass
class Lesson:
    """课时数据类"""
    title: str
    url: str
    transcript: str = ""


class CourseCrawler:
    """课程爬虫类"""
    
    BASE_URL = "https://learn.deeplearning.ai/courses/agent-skills-with-anthropic"
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.lessons: List[Lesson] = []
    
    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        # 设置视口大小
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
    
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
    
    async def get_lesson_links(self) -> List[Lesson]:
        """获取所有课时链接"""
        print("正在获取课程课时列表...")
        await self.page.goto(self.BASE_URL, wait_until="networkidle")
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        lessons = []
        
        # 尝试多种选择器来获取课时链接
        selectors = [
            'nav a[href*="/lesson/"]',
            '[data-testid="lesson-nav"] a',
            '.lesson-list a',
            'aside a[href*="/lesson/"]',
            'a[href*="/courses/agent-skills-with-anthropic/lesson/"]'
        ]
        
        for selector in selectors:
            try:
                links = await self.page.query_selector_all(selector)
                if links:
                    print(f"使用选择器 '{selector}' 找到 {len(links)} 个链接")
                    for link in links:
                        href = await link.get_attribute('href')
                        title = await link.inner_text()
                        
                        if href and title:
                            # 确保 URL 是完整的
                            if href.startswith('/'):
                                href = f"https://learn.deeplearning.ai{href}"
                            
                            # 清理标题
                            title = title.strip()
                            
                            # 避免重复
                            if not any(l.url == href for l in lessons):
                                lessons.append(Lesson(title=title, url=href))
                    
                    if lessons:
                        break
            except Exception as e:
                print(f"选择器 '{selector}' 失败: {e}")
                continue
        
        # 如果没有找到链接，尝试从页面源码中提取
        if not lessons:
            print("尝试从页面源码中提取课时链接...")
            content = await self.page.content()
            
            # 查找所有包含 lesson 的链接
            pattern = r'href="(/courses/agent-skills-with-anthropic/lesson/[^"]+)"[^>]*>([^<]+)<'
            matches = re.findall(pattern, content)
            
            for href, title in matches:
                full_url = f"https://learn.deeplearning.ai{href}"
                title = title.strip()
                if not any(l.url == full_url for l in lessons):
                    lessons.append(Lesson(title=title, url=full_url))
        
        print(f"共找到 {len(lessons)} 个课时")
        for i, lesson in enumerate(lessons, 1):
            print(f"  {i}. {lesson.title} -> {lesson.url}")
        
        self.lessons = lessons
        return lessons
    
    async def extract_transcript(self, lesson: Lesson) -> str:
        """从单个课时页面提取 Transcript"""
        print(f"\n正在爬取: {lesson.title}")
        print(f"URL: {lesson.url}")
        
        try:
            await self.page.goto(lesson.url, wait_until="networkidle")
            await asyncio.sleep(3)  # 等待动态内容加载
            
            transcript_text = ""
            
            # 策略 1: 查找包含 "Transcript" 文本的按钮或标签并点击
            transcript_button_selectors = [
                'button:has-text("Transcript")',
                '[role="tab"]:has-text("Transcript")',
                'a:has-text("Transcript")',
                'div:has-text("Transcript")',
                '[data-testid*="transcript"]',
                '[class*="transcript"]'
            ]
            
            for selector in transcript_button_selectors:
                try:
                    button = await self.page.query_selector(selector)
                    if button:
                        await button.click()
                        await asyncio.sleep(2)
                        print(f"  点击了 Transcript 按钮: {selector}")
                        break
                except Exception as e:
                    continue
            
            # 策略 2: 查找 Transcript 内容区域
            transcript_selectors = [
                '[data-testid="transcript-content"]',
                '[class*="transcript-content"]',
                '[class*="transcript-text"]',
                'div:has-text("Transcript") + div',
                '[role="tabpanel"]:has-text("Transcript")',
                'article[class*="transcript"]',
                '.transcript',
                '#transcript'
            ]
            
            for selector in transcript_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        transcript_text = await element.inner_text()
                        if transcript_text and len(transcript_text) > 50:
                            print(f"  使用选择器 '{selector}' 提取到 {len(transcript_text)} 字符")
                            break
                except Exception as e:
                    continue
            
            # 策略 3: 如果还没找到，尝试查找页面中所有可能包含字幕的大段文本
            if not transcript_text:
                print("  尝试查找页面中的大段文本...")
                paragraphs = await self.page.query_selector_all('p, div[class*="text"], div[class*="content"]')
                texts = []
                for p in paragraphs:
                    text = await p.inner_text()
                    if text and len(text) > 100:
                        texts.append(text)
                
                if texts:
                    # 选择最长的文本块（可能是字幕）
                    transcript_text = max(texts, key=len)
                    print(f"  从段落中提取到 {len(transcript_text)} 字符")
            
            # 策略 4: 检查是否有 "Show more" 或 "显示更多" 按钮
            show_more_selectors = [
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                'a:has-text("Show more")',
                '[class*="show-more"]',
                '[class*="load-more"]'
            ]
            
            for selector in show_more_selectors:
                try:
                    while True:
                        button = await self.page.query_selector(selector)
                        if not button:
                            break
                        await button.click()
                        await asyncio.sleep(1)
                        print(f"  点击了 'Show more' 按钮")
                        
                        # 重新获取内容
                        for sel in transcript_selectors:
                            element = await self.page.query_selector(sel)
                            if element:
                                new_text = await element.inner_text()
                                if new_text and len(new_text) > len(transcript_text):
                                    transcript_text = new_text
                except Exception as e:
                    break
            
            if transcript_text:
                # 清理文本
                transcript_text = self._clean_transcript(transcript_text)
                print(f"  成功提取字幕，长度: {len(transcript_text)} 字符")
            else:
                print(f"  警告: 未能提取到字幕内容")
                transcript_text = "[未能提取到字幕内容]"
            
            return transcript_text
            
        except Exception as e:
            print(f"  错误: 爬取失败 - {e}")
            return f"[爬取失败: {e}]"
    
    def _clean_transcript(self, text: str) -> str:
        """清理字幕文本"""
        # 移除多余的空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 移除常见的无关文本
        remove_patterns = [
            r'Transcript\s*',
            r'Show more\s*',
            r'Load more\s*',
            r'\[music\]\s*',
            r'\[Music\]\s*',
        ]
        
        for pattern in remove_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    async def crawl_all_lessons(self):
        """爬取所有课时的字幕"""
        if not self.lessons:
            await self.get_lesson_links()
        
        for i, lesson in enumerate(self.lessons, 1):
            print(f"\n[{i}/{len(self.lessons)}] ", end="")
            lesson.transcript = await self.extract_transcript(lesson)
            
            # 添加延迟，避免请求过快
            if i < len(self.lessons):
                await asyncio.sleep(2)
    
    def export_to_markdown(self, filename: str = "transcripts.md"):
        """导出到 Markdown 文件"""
        print(f"\n正在导出到 {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Agent Skills with Anthropic - 课程字幕\n\n")
            f.write("> 来源: https://learn.deeplearning.ai/courses/agent-skills-with-anthropic\n\n")
            f.write("---\n\n")
            
            for i, lesson in enumerate(self.lessons, 1):
                f.write(f"## 课时 {i}: {lesson.title}\n\n")
                f.write(f"**链接**: {lesson.url}\n\n")
                f.write("### Transcript\n\n")
                f.write(lesson.transcript)
                f.write("\n\n---\n\n")
        
        print(f"导出完成: {filename}")


async def main():
    """主函数"""
    crawler = CourseCrawler()
    
    try:
        # 初始化浏览器（非 headless 模式方便调试）
        print("正在启动浏览器...")
        await crawler.init_browser(headless=False)
        
        # 获取课时列表
        lessons = await crawler.get_lesson_links()
        
        if not lessons:
            print("未找到任何课时，请检查页面结构或网络连接")
            return
        
        # 爬取所有字幕
        await crawler.crawl_all_lessons()
        
        # 导出到 Markdown
        crawler.export_to_markdown("transcripts.md")
        
        print("\n✅ 爬取完成！")
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await crawler.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
