"""Job platform adapter package.

Exports the base class and all concrete platform implementations.
"""

from app.browser.adapters.base import BaseJobAdapter
from app.browser.adapters.naukri import NaukriAdapter
from app.browser.adapters.linkedin import LinkedInAdapter
from app.browser.adapters.indeed import IndeedAdapter

__all__ = ["BaseJobAdapter", "NaukriAdapter", "LinkedInAdapter", "IndeedAdapter"]

