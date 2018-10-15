import scrapy

class AbstractSpider(scrapy.Spider):
    name = "abstracts_fail"
    
    start_urls = ['https://academic.oup.com/jas/issue-archive']
    baseurl = 'https://academic.oup.com'
    
    def parse(self, response):

        #follow links to volumes
        try: 
            for href in response.xpath("//div[@class='widget widget-IssueYears widget-instance-OUP_Issues_Year_List']/div/a/@href").extract():
                url = self.baseurl + href
                yield scrapy.Request(url, callback=self.parse_volume)
        except:
            pass
        
    def parse_volume(self,response):
        
        
        #follow links to issues
        try:
            for href in response.xpath("//div[@id='item_ResourceLink']/a/@href").extract(): #@href optional for <a> elements?
                url = self.baseurl + href
                yield scrapy.Request(url, callback=self.parse_issue)
        except:
            pass
    def parse_issue(self, response):
        #follow links to articles
        try:
            for href in response.xpath("//a[@class='viewArticleLink']/@href").extract():
                url = self.baseurl + href
                yield scrapy.Request(url, callback=self.parse_article)
        except:
            pass
            
            
    def parse_article(self, response):
        #parse article
        def extract_with_xpath(query):
            return response.xpath(query).extract_first().strip()
        
        yield {
            'title': extract_with_xpath("//h1[@class='wi-article-title article-title-main']/text()"),
            'abstract': extract_with_xpath("//section[@class='abstract']/p/text()"),
            'doi': extract_with_xpath("//div[@class='ww-citation-primary']/a/@href"),
            'date': extract_with_xpath("//div[@class='ii-pub-date']/text()"),
            'citation': extract_with_xpath("//div[@class='ww-citation-primary']/text()"),
            'category': extract_with_xpath("//div[@class='article-metadata-tocSections']/a/text()")
        }
        