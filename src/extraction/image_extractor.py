from pathlib import Path

import fitz
import io


class PageImageExtractor:
    """
    Extracts embedded images from each PDF page and
    saves them under data/extracted/images/<exam_name>/.
    Returns a mapping: page_number -> [image filenames].
    """

    def __init__(
        self,
        pdf_path: str,
        exam_name: str,
        output_root: str = (
            "data/extracted/images"
        ),
    ):

        self.pdf_path = pdf_path

        self.exam_name = exam_name

        self.output_dir = (
            Path(output_root)
            / exam_name
        )

    def extract(
        self,
    ) -> dict[int, list[str]]:

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        result: dict[int, list[str]] = {}

        doc = fitz.open(self.pdf_path)

        try:

            for page_index, page in enumerate(
                doc
            ):

                page_number = (
                    page_index + 1
                )

                saved: list[str] = []

                images = (
                    page.get_images(full=True)
                )

                for img_index, img in enumerate(
                    images
                ):

                    xref = img[0]

                    try:

                        base = doc.extract_image(
                            xref
                        )

                        ext = base.get(
                            "ext",
                            "png",
                        )

                        # Convert JPX to PNG for wider compatibility
                        if ext.lower() == "jpx":
                            try:
                                from PIL import Image
                                img_data = base["image"]
                                image = Image.open(io.BytesIO(img_data))
                                ext = "png"
                                filename = (
                                    f"page{page_number}"
                                    f"_img{img_index + 1}"
                                    f".{ext}"
                                )
                                file_path = self.output_dir / filename
                                image.save(file_path, format="PNG")
                                saved.append(str(file_path))
                                continue # Skip default saving for JPX
                            except ImportError:
                                print(
                                    "[image] Pillow not installed. "
                                    "JPX images will be saved as is "
                                    "and may not be viewable."
                                )
                            except Exception as img_conv_e:
                                print(
                                    f"[image] page {page_number} img {img_index+1}: "
                                    f"Failed to convert JPX to PNG: {img_conv_e}"
                                )

                        filename = (
                            f"page{page_number}"
                            f"_img{img_index + 1}"
                            f".{ext}"
                        )

                        file_path = (
                            self.output_dir
                            / filename
                        )

                        file_path.write_bytes(
                            base["image"]
                        )

                        saved.append(
                            str(file_path)
                        )

                    except Exception as e:

                        print(
                            f"[image] page "
                            f"{page_number} "
                            f"img {img_index+1} "
                            f"failed: {e}"
                        )

                if saved:
                    result[page_number] = (
                        saved
                    )

        finally:

            doc.close()

        return result