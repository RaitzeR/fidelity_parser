import edgar
import csv
import re
from lxml.etree import tostring


class Parser():
    def __init__(self, name, cik, filingType):
        self.name = name
        self.cik = cik
        self.filingType = filingType
        self.data = []
        self.seriesData = {}
        self.seriesHeader = {}

    def parse(self):
        self.parseSeriesData()
        company = edgar.Company(self.name, self.cik)
        tree = company.getAllFilings(filingType=self.filingType)
        docs = edgar.getDocuments(tree, noOfDocuments=1)
        csv_file = open("test.csv", "wb")
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        for doc in docs:
            file = open("newFile.html", "w")
            file.write(tostring(doc))
            reports = doc.cssselect("div[style='font: normal 11pt Arial, Helvetica, sans-serif; width: 780px']")
            superData = []
            for report in reports:

                investment_table = report.cssselect("table")[0]

                rows = investment_table.cssselect("tr")
                series_name = investment_table.getparent().cssselect(
                    "p[style='font: bold 20pt Arial, Helvetica, sans-serif; margin-top: 0px;']")[0].text.strip().encode(
                    'ascii', errors="ignore")
                data = [["Filing Classification", "Holding Type", "Holding Name", "Holding Share", "Holding Value",
                         "Holding Face Amt", "Holding Number Of Contracts", "Future Gain Or Loss"]]
                total_holding_value = 0
                total_net_holding_value = 0
                total_share_value = 0
                for row in rows:
                    if len(row.getchildren()) == 4:
                        if row.get("style") == "font-weight:bold; color: #ffffff; background-color: #000000;":
                            classification = row.getchildren()[0].text.strip().split(" - ")[0].encode('utf-8')
                        if "NET OTHER ASSETS (LIABILITIES)" in row[0].text:
                            holding_value = abs(int(re.sub('[^0-9]', '',row[3].text.strip().encode('utf-8'))))
                            row = ["Liabilities, Net Of Other Assets",
                                   "Other",
                                   "Liabilities, Net Of Other Assets",
                                   "",
                                   holding_value,
                                   0, 0, 0]
                            total_net_holding_value -= holding_value
                            data.append(row)
                        elif row[0].text.strip() != "" and row[2].text.strip() != "" and row[3].text.strip() != "":
                            holding_share = int(re.sub('[^0-9]', '', row[2].text.strip().encode('utf-8')))
                            holding_value = int(re.sub('[^0-9]', '', row[3].text.strip().encode('utf-8')))
                            row = [classification,
                                   "Stock",
                                   row[0].text.strip().encode('utf-8'),
                                   holding_share,
                                   holding_value,
                                   0, 0, 0]
                            total_holding_value += holding_value
                            total_net_holding_value += holding_value
                            total_share_value += holding_share
                            data.append(row);
                self.seriesData[series_name]["total_stocks_value"] = total_share_value
                self.seriesData[series_name]["total_assets"] = total_holding_value
                self.seriesData[series_name]["total_net_assets"] = total_net_holding_value

                seriesDataArray = []
                for key in self.seriesData[series_name]["keys"]:
                    seriesDataArray.append(self.seriesData[series_name][key])
                data.insert(0,seriesDataArray)
                data.insert(0,self.seriesHeader[series_name])
                superData.append(data)
        for data in superData:
            csv_writer.writerows(data)


    def parseSeriesData(self):
        company = edgar.Company(self.name, self.cik)
        tree = company.getAllFilings(filingType=self.filingType)
        series = edgar.getSeriesTables(tree, noOfDocuments=1)
        seriesData = {}
        seriesHeader = {}
        filing_date = ""
        period_of_report = ""

        for serie in series:
            for infoHead in serie.cssselect(".infoHead"):
                if infoHead.text.strip() == "Filing Date":
                    filing_date = infoHead.getnext().text.strip().encode('utf-8')
                elif infoHead.text.strip() == "Period of Report":
                    period_of_report = infoHead.getnext().text.strip().encode('utf-8')
            for serieRows in serie.cssselect(".seriesName"):
                seriesNum = serieRows.cssselect("a")[0].text.strip().encode('utf-8')
                seriesName = serieRows.getnext().getnext().text.strip().encode('utf-8')
                classTickers = []
                rowsLeft = True
                nextRow = serieRows.getparent().getnext()
                while rowsLeft != False:
                    if nextRow == None:
                        break
                    if nextRow.get("class") != "contractRow":
                        break

                    classTickers.append(nextRow.cssselect("td:nth-child(4)")[0].text.strip().encode('utf-8'))
                    nextRow = nextRow.getnext()
                seriesArrayHeader = ["As of Date", "Filing Date", "CIK Number", "Series Number", "Series Name",
                                     "Total Stocks Value", "Total Assets", "Total Net Assets"]
                seriesArray = {}
                seriesArray["keys"] = ["period_of_report","filing_date","cik","series_number","series_name","total_stocks_value",
                                       "total_assets","total_net_assets"]
                seriesArray["period_of_report"] = period_of_report
                seriesArray["filing_date"] = filing_date
                seriesArray["cik"] = self.cik
                seriesArray["series_number"] = seriesNum
                seriesArray["series_name"] = seriesName
                seriesArray["total_stocks_value"] = 0
                seriesArray["total_assets"] = 0
                seriesArray["total_net_assets"] = 0
                i = 1
                for classTicker in classTickers:
                    seriesArray["ticker" + `i`] = classTicker
                    seriesArray["keys"].append("ticker" + `i`)
                    seriesArrayHeader.append("Series Ticker" + `i`)
                    i = i + 1

                seriesData[seriesName] = seriesArray
                seriesHeader[seriesName] = seriesArrayHeader

            print seriesData

        self.seriesData = seriesData
        self.seriesHeader = seriesHeader

    def parseFiles(self):
        print "asd"


parser = Parser("Fidelity", "315700", "N-Q")
parser.parse()
