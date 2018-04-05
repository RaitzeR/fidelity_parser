import edgar
import csv
from lxml.etree import tostring


class Parser():
    def __init__(self, name, cik, filingType):
        self.name = name
        self.cik = cik
        self.filingType = filingType

    def parse(self):
        company = edgar.Company(self.name, self.cik)
        tree = company.getAllFilings(filingType=self.filingType)
        docs = edgar.getDocuments(tree, noOfDocuments=1)
        csv_file = open("test.csv", "wb")
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        for doc in docs:
            file = open("newFile.html", "w")
            file.write(tostring(doc))
            reports = doc.cssselect("div[style='font: normal 11pt Arial, Helvetica, sans-serif; width: 780px']")
            for report in reports:
                headers = report.cssselect(
                    "p[style='font: bold 18pt Arial, Helvetica, sans-serif; margin-bottom: 0px;']")
                for header in headers:
                    print(header.getnext().text)

                investment_table = report.cssselect("table")[0]

                rows = investment_table.cssselect("tr")
                data = [["Filing Classification", "Holding Type", "Holding Name", "Holding Share", "Holding Value",
                         "Holding Face Amt", "Holding Number Of Contracts", "Future Gain Or Loss"]]
                for row in rows:
                    if len(row.getchildren()) == 4:
                        if row.get("style") == "font-weight:bold; color: #ffffff; background-color: #000000;":
                            classification = row.getchildren()[0].text.strip().split(" - ")[0].encode('utf-8')
                            print(row.getchildren()[0].text)
                        if "NET OTHER ASSETS (LIABILITIES)" in row[0].text:
                            value = row[3].text.strip().encode('utf-8')
                            row = ["Liabilities, Net Of Other Assets",
                                   "Other",
                                   "Liabilities, Net Of Other Assets",
                                   "",
                                   "-" + value,
                                   0, 0, 0]
                            data.append(row)
                        elif row[0].text.strip() != "" and row[2].text.strip() != "" and row[3].text.strip() != "":
                            row = [classification,
                                   "Stock",
                                   row[0].text.strip().encode('utf-8'),
                                   row[2].text.strip().encode('utf-8'),
                                   row[3].text.strip().encode('utf-8'),
                                   0,0,0]
                            data.append(row);

        csv_writer.writerows(data)


parser = Parser("Fidelity", "315700", "N-Q")
parser.parse()
