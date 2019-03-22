import edgar
import csv
import re
from lxml.etree import tostring


class Parser():
    def __init__(self, companyName="", CIK="", filingType="", beforeDate="", afterDate=""):
        self.name = companyName
        self.cik = CIK
        self.filingType = filingType
        self.beforeDate = beforeDate
        self.afterDate = afterDate
        self.data = []
        self.seriesData = {}
        self.seriesHeader = {}
        self.reportsSelector = ""
        self.nameSelector = ""

        company = edgar.Company(self.name, self.cik)
        self.tree = company.getAllFilings(filingType=self.filingType, priorTo=self.beforeDate, afterOf=self.afterDate,
                                          noOfEntries=100)

    def parse(self):
        self.parseSeriesData()
        if self.filingType == "N-Q":
            self.parseNQ()
        elif self.filingType == "N-CSR":
            self.parseNCSR()
        else:
            print "{} not implemented yet".format(self.filingType)
            return ""

        docs = edgar.getDocuments(self.tree, noOfDocuments=100)

        if len(docs) == 0:
            print "No Documents with the given parameters"
            return ""

        for doc in docs:
            file = open("newFile.html", "w")
            file.write(tostring(doc))
            # reports = doc.cssselect(self.reportsSelector)
            reports = doc.xpath("//p[contains(text(),'Showing Percentage of Net Assets')]")
            if len(reports) == 0:
                reports = doc.xpath("//font[contains(text(),'Showing Percentage of Net Assets')]")
            superData = []
            for report in reports:

                nameIndex = 0
                sharesIndex = 2
                valueIndex = 3

                if report.getnext() == None:
                    rows = report.getparent().getnext().cssselect("tr")
                else:
                    rows = report.getnext().cssselect("tr")

                series_name = self.getSeriesName(report)
                data = [["Filing Classification", "Holding Type", "Holding Name", "Holding Share", "Holding Value",
                         "Holding Face Amt", "Holding Number Of Contracts", "Future Gain Or Loss"]]
                total_holding_value = 0
                total_net_holding_value = 0
                total_share_value = 0
                for row in rows:
                    if len(row.getchildren()) == 4:
                        if len(row[0].cssselect("font")) != 0 or len(row[2].cssselect("font")) != 0 or len(
                                row[3].cssselect("font")) != 0:
                            row = row.cssselect('font')
                            if len(row) < 2:
                                continue
                        if len(row) == 2:
                            if row[0].text != None and "Shares" in row[0].text:
                                sharesIndex = 1
                            if row[1].text != None and "Shares" in row[1].text:
                                sharesIndex = 2
                            if row[0].text != None and "Value" in row[0].text:
                                valueIndex = 1
                            if row[1].text != None and "Value" in row[1].text:
                                valueIndex = 2
                        else:
                            nameIndex = 0
                            sharesIndex = 2
                            valueIndex = 3

                        if len(row) < 3:
                            continue
                        try:
                            if row.get("style") == "font-weight:bold; color: #ffffff; background-color: #000000;":
                                classification = row.getchildren()[0].text.strip().split(" - ")[0].encode('utf-8')
                        except AttributeError:
                            #TODO: Figure out a way to get the classification here on the older format
                            classification = "Test"

                        if "NET OTHER ASSETS (LIABILITIES)" in row[nameIndex].text:
                            holding_value = abs(int(re.sub('[^0-9]', '', row[valueIndex].text.strip().encode('utf-8'))))
                            row = ["Liabilities, Net Of Other Assets",
                                   "Other",
                                   "Liabilities, Net Of Other Assets",
                                   "",
                                   holding_value,
                                   0, 0, 0]
                            total_net_holding_value -= holding_value
                            data.append(row)
                        elif row[valueIndex].text == None:
                            continue
                        elif row[nameIndex].text.strip() != "" and row[sharesIndex].text.strip() != "" and row[
                            valueIndex].text.strip() != "" and len(row) > 2:
                            holding_share = int(re.sub('[^0-9]', '', row[sharesIndex].text.strip().encode('utf-8')))
                            holding_value = int(re.sub('[^0-9]', '', row[valueIndex].text.strip().encode('utf-8')))
                            row = [classification,
                                   "Stock",
                                   row[nameIndex].text.strip().encode('utf-8'),
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
                data.insert(0, seriesDataArray)
                data.insert(0, self.seriesHeader[series_name])

                csv_file = open("{} - {}.csv".format(series_name, self.seriesData[series_name]["filing_date"]), "wb")
                csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
                csv_writer.writerows(data)
                csv_file.close()

                superData.append(data)
        # for data in superData:
        #    csv_writer.writerows(data)

    def parseNQ(self):
        self.reportsSelector = "div[style='font: normal 11pt Arial, Helvetica, sans-serif; width: 780px']"
        self.nameSelector = "p[style='font: bold 20pt Arial, Helvetica, sans-serif; margin-top: 0px;']"

    def parseNCSR(self):
        self.reportsSelector = 'div[style="font: 11pt \'Times New Roman\', serif; width: 780px"]'
        self.nameSelector = "p[style='font: bold 20pt Arial, Helvetica, sans-serif; margin-bottom: 0px;']"

    def getSeriesName(self, report):
        if self.filingType == "N-Q":
            if len(report.getparent().cssselect(self.nameSelector)) == 0:
                fulltitle = ""
                foundTitle = False
                prevElement = report.getparent().getprevious()
                while foundTitle == False:
                    if self.name in tostring(prevElement):
                        foundElement = prevElement
                        foundTitle = True
                        break
                    prevElement = prevElement.getprevious()

                for titlePart in prevElement.cssselect("font[size='+2']"):
                    if len(titlePart.cssselect('b')) == 0:
                        if titlePart.text != None:
                            fulltitle = fulltitle + " " + re.sub(' +', ' ', titlePart.text.strip().encode('ascii',
                                                                                                          errors="ignore"))
                    else:
                        if titlePart.cssselect('b')[0].text != None:
                            fulltitle = fulltitle + " " + re.sub(' +', ' ',
                                                                 titlePart.cssselect('b')[0].text.strip().encode(
                                                                     'ascii',
                                                                     errors="ignore"))
                finalTitle = re.sub(" +", " ", fulltitle).strip()
                # print finalTitle
                # print tostring(
                #    report.getparent().getprevious().getprevious().getprevious().getprevious().getprevious().cssselect(
                #        "font")[0])
                # print tostring(
                #    report.getparent().getprevious().getprevious().getprevious().getprevious().getprevious().cssselect(
                #        "font")[1])
                # print tostring(
                #    report.getparent().getprevious().getprevious().getprevious().getprevious().getprevious().cssselect(
                #        "font")[2])
                return finalTitle
            else:
                return report.getparent().cssselect(self.nameSelector)[0].text.strip().encode('ascii', errors="ignore")
        elif self.filingType == "N-CSR":
            if report.getprevious().getprevious().text == None:
                return report.getparent().cssselect(self.nameSelector)[0].text.strip().encode('ascii', errors="ignore")
            return report.getprevious().getprevious().text.strip().encode('ascii', errors="ignore")
        else:
            print "{} type not implemented".format(self.filingType)

    def parseSeriesData(self):
        series = edgar.getSeriesTables(self.tree, noOfDocuments=100)
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
                seriesArray["keys"] = ["period_of_report", "filing_date", "cik", "series_number", "series_name",
                                       "total_stocks_value",
                                       "total_assets", "total_net_assets"]
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


#parser = Parser(companyName="Fidelity", CIK="315700", filingType="N-Q", beforeDate="20140101", afterDate="20130101")
parser = Parser(companyName="Fidelity",CIK="315700",filingType="N-Q",beforeDate="20170101",afterDate="20160101")
parser.parse()
