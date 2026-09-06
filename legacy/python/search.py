import requests
from typing import List, Dict
from bs4 import BeautifulSoup # pyright: ignore[reportMissingImports]

class WebReferenceSearch:
    """
    Lightweight internet reference tool.
    Queries Google/Bing and returns top page titles + URLs.
    Minimal scraping for research context.
    """

    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64)"

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if self.engine == "google":
            return self._google_search(query, max_results)
        else:
            return self._bing_search(query, max_results)

    def _google_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num={max_results}"
        headers = {"User-Agent": self.USER_AGENT}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for g in soup.find_all("div", class_="tF2Cxc")[:max_results]:
            title = g.find("h3")
            link = g.find("a")
            if title and link:
                results.append({"title": title.text, "url": link['href']})
        return results

    def _bing_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        headers = {"User-Agent": self.USER_AGENT}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.find_all("li", class_="b_algo")[:max_results]:
            a = item.find("a")
            h2 = item.find("h2")
            if a and h2:
                results.append({"title": h2.text, "url": a['href']})
        return results


