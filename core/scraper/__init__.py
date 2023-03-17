# core/scraper/__init__.py
from core.scraper.vivense import VivenseScraper
from core.scraper.koctas import KoctasScraper


class ScraperFactory:
    @staticmethod
    def get_vendor_scraper_by_name(vendor_name: str):
        if vendor_name.lower() == "vivense":
            return VivenseScraper

        if vendor_name.lower() == "koctas":
            return KoctasScraper

        # Add more scraper classes here as needed
        else:
            raise ValueError(f"Unsupported vendor '{vendor_name}'")



