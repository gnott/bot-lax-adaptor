import os, sys, json, re
import conf
import jsonschema

import logging
LOG = logging.getLogger(__name__)

# output to adaptor.log
_handler = logging.FileHandler("validate.log")
_handler.setLevel(logging.ERROR)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)

# output to screen
_handler2 = logging.StreamHandler()
_handler2.setLevel(logging.INFO)
_handler2.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
LOG.addHandler(_handler2)

placeholder_version = 1

placeholder_authors = [{
    "type": "person",
    "name": {
        "preferred": "Lee R Berger",
        "index": "Berger, Lee R"
    },
    "affiliations": [{
        "name": [
            "Evolutionary Studies Institute and Centre of Excellence in PalaeoSciences",
            "University of the Witwatersrand"
        ],
        "address": {
            "formatted": [
                "Johannesburg",
                "South Africa"
            ],
            "components": {
                "locality": [
                    "Johannesburg"
                ],
                "country": "South Africa"
            }
        }
    }]
}]

placeholder_references = [{
    "type": "journal",
    "id": "bib1",
    "date": "2008",
    "authors": [
        {
            "type": "person",
            "name": {
                "preferred": "Person One",
                "index": "One, Person"
            }
        }
    ],
    "articleTitle": "Auxin influx carriers stabilize phyllotactic patterning",
    "journal": {
        "name": [
            "Genes & Development"
        ]
    },
    "volume": "22",
    "pages": {
        "first": "810",
        "last": "823",
        "range": u"810\u2013823"
    },
    "doi": "10.1101/gad.462608"
}]

def uri_rewrite(body_json):
    base_uri = "https://example.org/"
    # Check if it is not a list, in the case of authorResponse
    if "content" in body_json:
        uri_rewrite(body_json["content"])
    # A list, like in body, continue
    for element in body_json:
        if (("type" in element and element["type"] == "image") or
                ("mediaType" in element)):
            if "uri" in element:
                element["uri"] = base_uri + element["uri"]
                # Add or edit file extension
                # TODO!!
        for content_index in ["content", "supplements", "sourceData"]:
            if content_index in element:
                try:
                    uri_rewrite(element[content_index])
                except TypeError:
                    # not iterable
                    pass
    return body_json

def video_rewrite(body_json):
    for element in body_json:
        if "type" in element and element["type"] == "video":
            if "uri" in element:
                element["sources"] = []
                source_media = {}
                source_media["mediaType"] = "video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\""
                source_media["uri"] = "https://example.org/" + element.get("uri")
                element["sources"].append(source_media)

                element["image"] = "https://example.org/" + element.get("uri")
                element["width"] = 640
                element["height"] = 480

                del element["uri"]

        for content_index in ["content"]:
            if content_index in element:
                try:
                    video_rewrite(element[content_index])
                except TypeError:
                    # not iterable
                    pass

    return body_json

def mathml_rewrite(body_json):
    # Check if it is not a list, in the case of authorResponse
    if "content" in body_json:
        mathml_rewrite(body_json["content"])
    # A list, like in body, continue
    for element in body_json:
        if "type" in element and element["type"] == "mathml":
            if "mathml" in element:
                # Quick edits to get mathml to comply with the json schema
                mathml = "<math>" + element["mathml"] + "</math>"
                mathml = mathml.replace("<mml:", "<").replace("</mml:", "</")
                element["mathml"] = mathml

        for content_index in ["content", "caption", "supplements"]:
            if content_index in element:
                try:
                    mathml_rewrite(element[content_index])
                except TypeError:
                    # not iterable
                    pass
    return body_json

def fix_image_attributes_if_missing(body_json):
    """
    Should be completely temporary - the schema does not allow images
    without certain attributes, so add them in in order to check for
    other parsing and validation issues
    """

    placeholder_image_title = "This a placeholder for a missing image title"

    # Check if it is not a list, in the case of authorResponse
    if "content" in body_json:
        fix_image_attributes_if_missing(body_json["content"])
    # A list, like in body, continue
    for element in body_json:
        if "type" in element and element["type"] == "image":
            if "title" not in element:
                element["title"] = placeholder_image_title

        for content_index in ["content", "supplements", "sourceData"]:
            if content_index in element:
                try:
                    fix_image_attributes_if_missing(element[content_index])
                except TypeError:
                    # not iterable
                    pass

    return body_json

def generate_section_id():
    """section id attribute generator"""
    global section_id_counter
    try:
        section_id_counter = section_id_counter + 1
    except (NameError, TypeError):
        section_id_counter = 1
    return "phantom-s-" + str(section_id_counter)

def fix_section_id_if_missing(body_json):
    for element in body_json:
        if "type" in element and element["type"] == "section":
            if "id" not in element:
                element["id"] = generate_section_id()
        for content_index in ["content"]:
            if content_index in element:
                try:
                    fix_section_id_if_missing(element[content_index])
                except TypeError:
                    # not iterable
                    pass

    return body_json

def fix_box_title_if_missing(body_json):
    placeholder_box_title_if_missing = "Placeholder box title because we must have one"
    for element in body_json:
        if "type" in element and element["type"] == "box":
            if "title" not in element:
                element["title"] = placeholder_box_title_if_missing
        for content_index in ["content"]:
            if content_index in element:
                try:
                    fix_box_title_if_missing(element[content_index])
                except TypeError:
                    # not iterable
                    pass
    return body_json

def wrap_body_in_section(body_json):
    """JSON schema requires body to be wrapped in a section even if not present"""

    if (body_json and len(body_json) > 0 and "type" in body_json[0]
            and body_json[0]["type"] != "section"):
        # Wrap this one
        new_body_section = {}
        new_body_section["type"] = "section"
        new_body_section["id"] = generate_section_id()
        new_body_section["title"] = ""
        new_body_section["content"] = []
        for body_block in body_json:
            new_body_section["content"].append(body_block)
        new_body = []
        new_body.append(new_body_section)
        body_json = new_body

    # Continue with rewriting
    return body_json

def references_rewrite(references):
    "clean up values that will not pass validation temporarily"
    for ref in references:
        if "date" in ref:
            # Scrub non-numeric values from the date, which comes from the reference year
            ref["date"] = re.sub("[^0-9]", "", ref["date"])
        if ref.get("type") == "other":
            # The schema cannot support type other, turn this into a basic journal reference
            #  to pass validation
            ref["type"] = "journal"
            #if not "articleTitle" in ref:
            #    ref["articleTitle"] = "Placeholder article title for ref of type 'other'"
            if not "journal" in ref:
                ref["journal"] = {}
                ref["journal"]["name"] = []
                #ref["journal"]["name"].append("This is a transformed placeholder journal name for ref of type 'other'")
                if "source" in ref:
                    ref["journal"]["name"].append(ref["source"])
                    del ref["source"]
        if ref.get("type") == "journal" and not "pages" in ref:
            #ref["pages"] = "placeholderforrefwithnopages"
            pass
        if ref.get("type") == "book":
            if not "publisher" in ref:
                ref["publisher"] = {}
                ref["publisher"]["name"] = []
                #ref["publisher"]["name"].append("This is a placeholder book publisher name for ref that does not have one")

    return references

def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False

def add_placeholders_for_validation(contents):
    art = contents['article']

    art['version'] = placeholder_version
    art['authors'] = placeholder_authors
    art['statusDate'] = '2016-01-01T00:00:00Z'

    # relatedArticles are not part of article deliverables
    if 'relatedArticles' in art:
        del art['relatedArticles']

    if 'references' in art:
        art['references'] = references_rewrite(placeholder_references)

    if 'published' not in art:
        art['published'] = '1970-07-01T00:00:00Z'

    for elem in ['body', 'decisionLetter', 'authorResponse']:
        if elem in art:
            art[elem] = uri_rewrite(art[elem])
            art[elem] = video_rewrite(art[elem])
            art[elem] = fix_section_id_if_missing(art[elem])
            art[elem] = mathml_rewrite(art[elem])
            art[elem] = fix_image_attributes_if_missing(art[elem])
            art[elem] = fix_box_title_if_missing(art[elem])

    for elem in ['body']:
        if elem in art:
            art[elem] = wrap_body_in_section(art[elem])


    if not is_poa(contents):
        pass

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', type=argparse.FileType('r'), default=sys.stdin)
    args = parser.parse_args()

    contents = json.load(args.infile)
    add_placeholders_for_validation(contents)

    schema = conf.POA_SCHEMA if is_poa(contents) else conf.VOR_SCHEMA

    filename = os.path.basename(args.infile.name)
    _, msid, tail = filename.split('-')
    ver, _ = tail.split('.', 1)

    log_context = {
        'json-filename': filename,
        'msid': msid,
        'version': ver
    }

    try:
        jsonschema.validate(contents["article"], schema)
        LOG.info("validated %s", msid, extra=log_context)
    except jsonschema.ValidationError as err:
        LOG.error("failed to validate %s: %s", msid, err.message, extra=log_context)
        exit(1)
    except KeyboardInterrupt:
        exit(1)

if __name__ == '__main__':
    main()
