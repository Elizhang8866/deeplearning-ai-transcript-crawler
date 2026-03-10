"""
DeepLearning.AI Agent Skills 课程 Transcript 爬虫（带登录支持）
爬取课程所有课时的视频字幕并整理到 Markdown 文件

使用方法:
1. 运行脚本后会自动打开浏览器
2. 在浏览器中手动登录 DeepLearning.AI 账号
3. 登录完成后在终端按 Enter 键继续
4. 脚本会自动爬取所有课时的字幕
"""

import asyncio
import re
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
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
    COOKIES_FILE = "cookies.json"
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.lessons: List[Lesson] = []
        self.playwright = None
    
    async def init_browser(self, headless: bool = False):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        # 添加更多浏览器启动选项
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # 创建新页面并设置视口
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        
        # 设置用户代理
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def manual_login(self):
        """手动登录流程"""
        print("\n" + "="*60)
        print("请在新打开的浏览器窗口中完成以下操作：")
        print("1. 访问 DeepLearning.AI 网站")
        print("2. 点击 'Sign In' 登录您的账号")
        print("3. 登录成功后，返回到课程页面:")
        print(f"   {self.BASE_URL}")
        print("4. 确认可以看到课程内容后，")
        print("   请在此终端按 Enter 键继续...")
        print("="*60 + "\n")
        
        # 尝试访问主站而不是登录页面
        try:
            await self.page.goto("https://learn.deeplearning.ai", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"访问主站失败: {e}")
            print("尝试直接访问课程页面...")
            try:
                await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
            except:
                pass
        
        # 等待用户按 Enter
        input()
        
        print("继续执行爬取...")
        await asyncio.sleep(2)
    
    async def get_lesson_links(self) -> List[Lesson]:
        """获取所有课时链接"""
        print("\n正在获取课程课时列表...")
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)
                break
            except Exception as e:
                print(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    print("无法访问课程页面，请检查网络连接")
                    return []
        
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
        
        print(f"\n共找到 {len(lessons)} 个课时")
        for i, lesson in enumerate(lessons, 1):
            print(f"  {i}. {lesson.title}")
        
        self.lessons = lessons
        return lessons
    
    async def extract_transcript(self, lesson: Lesson) -> str:
        """从单个课时页面提取 Transcript"""
        print(f"\n[{self.lessons.index(lesson) + 1}/{len(self.lessons)}] 正在爬取: {lesson.title}")
        
        try:
            # 重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.page.goto(lesson.url, wait_until="networkidle", timeout=60000)
                    await asyncio.sleep(3)
                    break
                except Exception as e:
                    print(f"  第 {attempt + 1} 次尝试失败: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                    else:
                        return "[页面加载失败]"
            
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
                        print(f"  点击了 Transcript 按钮")
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
                
                # 尝试查找常见的字幕容器
                container_selectors = [
                    '[class*="video-transcript"]',
                    '[class*="lesson-transcript"]',
                    '[class*="caption"]',
                    '[class*="subtitle"]',
                    'article',
                    'main [class*="content"]',
                    '[class*="lesson-content"]'
                ]
                
                for selector in container_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for elem in elements:
                            text = await elem.inner_text()
                            if text and len(text) > 200:
                                transcript_text = text
                                print(f"  从容器 '{selector}' 提取到 {len(text)} 字符")
                                break
                        if transcript_text:
                            break
                    except:
                        continue
            
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
                    click_count = 0
                    while click_count < 10:  # 最多点击10次
                        button = await self.page.query_selector(selector)
                        if not button:
                            break
                        
                        # 检查按钮是否可见
                        is_visible = await button.is_visible()
                        if not is_visible:
                            break
                            
                        await button.click()
                        await asyncio.sleep(1)
                        click_count += 1
                        print(f"  点击了 'Show more' 按钮 ({click_count})")
                        
                        # 重新获取内容
                        for sel in transcript_selectors:
                            element = await self.page.query_selector(sel)
                            if element:
                                new_text = await element.inner_text()
                                if new_text and len(new_text) > len(transcript_text):
                                    transcript_text = new_text
                    
                    if click_count > 0:
                        print(f"  共点击了 {click_count} 次 'Show more'")
                        
                except Exception as e:
                    break
            
            if transcript_text:
                # 清理文本
                transcript_text = self._clean_transcript(transcript_text)
                print(f"  ✅ 成功提取字幕，长度: {len(transcript_text)} 字符")
            else:
                print(f"  ⚠️  未能提取到字幕内容")
                transcript_text = "[未能提取到字幕内容]"
            
            return transcript_text
            
        except Exception as e:
            print(f"  ❌ 错误: 爬取失败 - {e}")
            return f"[爬取失败: {e}]"
    
    def _clean_transcript(self, text: str) -> str:
        """清理字幕文本"""
        # 移除多余的空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 移除常见的无关文本
        remove_patterns = [
            r'^Transcript\s*',
            r'Show more\s*',
            r'Load more\s*',
            r'\[music\]\s*',
            r'\[Music\]\s*',
        ]
        
        for pattern in remove_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        return text.strip()
    
    async def crawl_all_lessons(self):
        """爬取所有课时的字幕"""
        if not self.lessons:
            await self.get_lesson_links()
        
        for i, lesson in enumerate(self.lessons, 1):
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
        
        print(f"✅ 导出完成: {filename}")
    
    def save_progress(self, filename: str = "progress.json"):
        """保存进度到 JSON 文件"""
        data = {
            "lessons": [asdict(lesson) for lesson in self.lessons]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"进度已保存到: {filename}")


async def main():
    """主函数"""
    crawler = CourseCrawler()
    
    try:
        # 初始化浏览器（非 headless 模式，方便用户手动登录）
        print("正在启动浏览器...")
        await crawler.init_browser(headless=False)
        
        # 手动登录流程
        await crawler.manual_login()
        
        # 获取课时列表
        lessons = await crawler.get_lesson_links()
        
        if not lessons:
            print("未找到任何课时，请检查页面结构或网络连接")
            return
        
        # 爬取所有字幕
        await crawler.crawl_all_lessons()
        
        # 导出到 Markdown
        crawler.export_to_markdown("transcripts.md")
        
        # 保存进度
        crawler.save_progress("progress.json")
        
        print("\n" + "="*60)
        print("✅ 爬取完成！")
        print("="*60)
        print(f"\n生成的文件:")
        print(f"  - transcripts.md: 课程字幕 Markdown 文件")
        print(f"  - progress.json: 爬取进度 JSON 文件")
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await crawler.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
