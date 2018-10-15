import scrapy
from w3lib.html import remove_tags #remove html tags

class AbstractSpider(scrapy.Spider):
    name = "abstracts"
    
    # OUP site is organized like ' list of volumes (basically year) 
    #                              > list of issues (several per year) 
    #                              > list of Articles'
    
    # start url is a page with a list of volumes with urls
    start_urls = ['https://academic.oup.com/jas/issue-archive']
    baseurl = 'https://academic.oup.com'
    
    def parse(self, response):

        #follow links to volumes
        try: 
            for href in response \
                    .xpath("//div[@class='widget widget-IssueYears widget-instance-OUP_Issues_Year_List']/div/a/@href") \
                    .extract():
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
            return remove_tags(response.xpath(query).extract_first()).strip()
        
        # many fields of interest within the same tag
        citation = extract_with_xpath("//div[@class='ww-citation-primary']").split(', ')
        
        yield {
            'title': extract_with_xpath("//h1[@class='wi-article-title article-title-main']"),
            'abstract': extract_with_xpath("//section[@class='abstract']"),
            'doi': citation[5],
            'date': citation[3],
            'Journal': citation[0],
            'Volume':citation[1],
            'Issue': citation[2],
            'Pages': citation[4],
            'category': extract_with_xpath("//div[@class='article-metadata-tocSections']/a")
        }
        