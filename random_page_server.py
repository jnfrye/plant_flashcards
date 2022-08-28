import webbrowser
import os
import random
import time
from jinja2 import Environment, FileSystemLoader

import photo_loader as pl


PHOTOS_ROOT = pl.CACHED_PHOTOS_ROOT


def main():
    taxon = get_taxon()
    open_taxon_page(taxon)
    taxon_results = get_all_inputs()
    save_results(taxon, taxon_results)


def get_taxon():
    return get_random_taxon()


def get_random_taxon():
    all_taxons = pl.get_all_taxons()
    return random.choice(all_taxons)


def open_taxon_page(taxon):
    pl.ensure_photos_cached(taxon)
    
    photo_files = os.listdir(PHOTOS_ROOT + "/" + "/".join(taxon))
    photos = ["/".join(taxon) + "/" + x for x in photo_files]
    
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("template.html")
    flashcard_html = template.render(photos=photos, family=taxon[0], genus=taxon[1], species=taxon[2])
    
    with open(PHOTOS_ROOT + "/flashcard.html", 'w') as f:
        f.write(flashcard_html)
    
    webbrowser.open(os.path.abspath(PHOTOS_ROOT + "/flashcard.html"))


def get_all_inputs():
    family_input = get_input("FAMILY")
    genus_input = get_input("GENUS")
    species_input = get_input("SPECIES")
    
    return (family_input, genus_input, species_input)


def get_input(taxon_level):
    result = input("Type '1' if you guessed " + taxon_level + " correctly, '0' otherwise.\n")
    result = "0" if result == "" else result
    return result


def save_results(taxon, taxon_results):
    with open("flashcard_guess_results.csv", 'a') as f:
        f.write(f"{int(time.time())},{','.join(taxon)},{','.join(taxon_results)}\n")


if __name__ == "__main__":
    main()