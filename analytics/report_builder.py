class ReportBuilder:

    def __init__(self):

        self.lines = []

    def title(self, text):

        self.lines.append("=" * 60)
        self.lines.append(text)
        self.lines.append("=" * 60)

    def add(self, text):

        self.lines.append(text)

    def build(self):

        return "\n".join(self.lines)