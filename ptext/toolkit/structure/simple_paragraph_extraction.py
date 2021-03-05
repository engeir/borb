import typing
from decimal import Decimal

from ptext.pdf.canvas.datastructure.disjoint_set import disjointset
from ptext.pdf.canvas.geometry.rectangle import Rectangle
from ptext.pdf.canvas.layout.paragraph import Paragraph, LayoutElement
from ptext.pdf.page.page import Page
from ptext.toolkit.structure.simple_line_of_text_extraction import (
    SimpleLineOfTextExtraction,
)


class SimpleParagraphExtraction(SimpleLineOfTextExtraction):
    def __init__(
        self,
        minimum_horizontal_overlap_percentage: Decimal = Decimal(0.80),
        maximum_multiplied_leading: Decimal = Decimal(1.40),
    ):
        super(SimpleParagraphExtraction, self).__init__()
        self.minimum_horizontal_overlap_percentage = (
            minimum_horizontal_overlap_percentage
        )
        self.maximum_multiplied_leading = maximum_multiplied_leading
        self.paragraphs_per_page: typing.Dict[int, typing.List[Paragraph]] = {}

    def _end_page(self, page: Page):
        super(SimpleParagraphExtraction, self)._end_page(page)

        # build initial disjointset
        line_of_text_disjoint_set = disjointset()
        for line_of_text in self.lines_of_text_per_page[self.current_page_number]:
            line_of_text_disjoint_set.add(line_of_text)

        # merge all LineOfText objects that represent a line of text
        for l0 in line_of_text_disjoint_set:
            for l1 in line_of_text_disjoint_set:
                if l0 == l1:
                    continue
                if line_of_text_disjoint_set.find(l0) == line_of_text_disjoint_set.find(
                    l1
                ):
                    continue

                # determine overlap
                overlap_percentage = self._overlap(
                    l0.bounding_box, l1.bounding_box
                ) / min(l0.bounding_box.width, l1.bounding_box.width)

                # determine leading
                leading = abs(l0.bounding_box.y - l1.bounding_box.y) / min(
                    l0.bounding_box.height, l1.bounding_box.height
                )

                if (
                    overlap_percentage >= self.minimum_horizontal_overlap_percentage
                    and leading <= self.maximum_multiplied_leading
                ):
                    line_of_text_disjoint_set.union(l0, l1)
                    break

        # combine partitions into Paragraph objects
        paragraphs: typing.List[Paragraph] = []
        for line_of_text_partition in line_of_text_disjoint_set.sets():
            lines_of_text = [x for x in line_of_text_partition]

            # determine text
            txt = "".join([x.text + "\n" for x in lines_of_text])[:-1]

            # create / append paragraph
            p: LayoutElement = Paragraph(
                text=txt,
                font=lines_of_text[0].font,
                font_color=lines_of_text[0].font_color,
                font_size=lines_of_text[0].font_size,
            ).set_bounding_box(
                Rectangle(
                    min([l.bounding_box.x for l in lines_of_text]),
                    min([l.bounding_box.y for l in lines_of_text]),
                    max(
                        [l.bounding_box.x + l.bounding_box.width for l in lines_of_text]
                    )
                    - min([l.bounding_box.x for l in lines_of_text]),
                    max(
                        [
                            l.bounding_box.y + l.bounding_box.height
                            for l in lines_of_text
                        ]
                    )
                    - min([l.bounding_box.y for l in lines_of_text]),
                )
            )
            assert isinstance(p, Paragraph)
            paragraphs.append(p)

        # add to dict
        self.paragraphs_per_page[self.current_page_number] = paragraphs

    def get_paragraphs(self, page: int) -> typing.List[Paragraph]:
        return self.paragraphs_per_page.get(page, [])

    def _overlap(self, r0: Rectangle, r1: Rectangle) -> Decimal:
        # rectangles do not overlap (r0 is on the left side)
        if max(r0.x, r0.x + r0.width) < min(r1.x, r1.x + r1.width):
            return Decimal(0)
        # rectangles do not overlap (r1 is on the left side)
        if max(r1.x, r1.x + r1.width) < min(r0.x, r0.x + r0.width):
            return Decimal(0)
        a = max(min(r0.x, r0.x + r0.width), min(r1.x, r1.x + r1.width))
        b = min(max(r0.x, r0.x + r0.width), max(r1.x, r1.x + r1.width))
        return abs(a - b)
