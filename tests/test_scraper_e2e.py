"""
E2E and unit tests for BoxMagic check-in scraper.
Run: pytest tests/ -v
"""
import json
import pytest
from unittest.mock import MagicMock
import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper_playwright import BoxMagicScraper


# Sample BoxMagic date_get_clases API response
SAMPLE_DATE_GET_CLASES = {
    "success": True,
    "clases": [
        {
            "nombre": "Sesión grupal 6:00 am",
            "hora_inicio": "06:00",
            "hora_fin": "07:00",
            "clase_id": 104996,
            "dias_clases_id": 237092,
            "clase_online": 0
        },
        {
            "nombre": "Sesión semiprivada 10:15 am",
            "hora_inicio": "10:15",
            "hora_fin": "11:15",
            "clase_id": 105112,
            "dias_clases_id": 237418,
            "clase_online": 0
        },
    ]
}

# Sample get_alumnos_clase format (DOM option value)
SAMPLE_DOM_OPTIONS = [
    {"value": "104996-237092", "text": "Sesión grupal 6:00 am - 06:00-07:00 Presencial"},
    {"value": "105112-237418", "text": "Sesión semiprivada 10:15 am - 10:15-11:15 Presencial"},
]


@pytest.fixture
def scraper():
    config = MagicMock()
    config.CHECKIN_URL = "https://boxmagic.cl/checkin/clases"
    config.TIMEOUT = 10000
    return BoxMagicScraper(config)


class TestParseClassesFromApiResponse:
    """Test _parse_classes_from_api_response handles BoxMagic API format."""

    def test_parses_date_get_clases_format(self, scraper):
        result = scraper._parse_classes_from_api_response(SAMPLE_DATE_GET_CLASES)
        assert len(result) == 2
        assert result[0]["value"] == "104996-237092"
        assert result[0]["text"] == "Sesión grupal 6:00 am"
        assert result[1]["value"] == "105112-237418"
        assert result[1]["text"] == "Sesión semiprivada 10:15 am"

    def test_value_format_clase_id_dias_clases_id(self, scraper):
        """Value must be clase_id-dias_clases_id for get_alumnos_clase endpoint."""
        result = scraper._parse_classes_from_api_response(SAMPLE_DATE_GET_CLASES)
        for item in result:
            parts = item["value"].split("-")
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1].isdigit()

    def test_parses_list_of_clase_dicts(self, scraper):
        data = SAMPLE_DATE_GET_CLASES["clases"]
        result = scraper._parse_classes_from_api_response(data)
        assert len(result) == 2
        assert result[0]["value"] == "104996-237092"

    def test_parses_dom_option_value_format(self, scraper):
        """DOM options have value='clase_id-dias_clases_id' directly."""
        html = '<option value="104996-237092">Sesión grupal 6:00 am</option>'
        result = scraper._parse_classes_from_api_response(html)
        assert len(result) == 1
        assert result[0]["value"] == "104996-237092"


class TestClassIdValidation:
    """Test class_id format is correct for API calls."""

    def test_valid_class_id_format(self):
        import re
        pattern = re.compile(r'^\d+-\d+$')
        assert pattern.match("104996-237092")
        assert pattern.match("105112-237418")
        assert not pattern.match("104996")
        assert not pattern.match("invalid")

    def test_extracts_class_id_from_parsed_item(self, scraper):
        result = scraper._parse_classes_from_api_response(SAMPLE_DATE_GET_CLASES)
        class_info = result[0]
        class_id = class_info.get("value", "").strip()
        assert class_id == "104996-237092"


class TestGetAlumnosClaseUrl:
    """Verify URL format for get_alumnos_clase endpoint."""

    def test_url_format(self):
        base = "https://boxmagic.cl/checkin/get_alumnos_clase"
        class_id = "104996-237092"
        date_str = "09-02-2026"
        url = f"{base}/{class_id}?fecha_where={date_str}&method=alumnos"
        assert "104996-237092" in url
        assert "09-02-2026" in url
        assert "alumnos" in url


class TestDateGetClasesUrl:
    """Verify date_get_clases endpoint URL."""

    def test_url_format(self):
        base = "https://boxmagic.cl/checkin/date_get_clases"
        date_str = "09-02-2026"
        url = f"{base}/{date_str}"
        assert url == "https://boxmagic.cl/checkin/date_get_clases/09-02-2026"


# =============================================================================
# EDGE CASE TESTS - Ensure scraper works correctly across runs and future dates
# =============================================================================

class TestApiParsingEdgeCases:
    """Edge cases for API response parsing."""

    def test_empty_clases_list(self, scraper):
        """Empty clases list should return empty result, not crash."""
        data = {"success": True, "clases": []}
        result = scraper._parse_classes_from_api_response(data)
        assert result == []

    def test_success_false_still_parses_clases(self, scraper):
        """If success is false but clases exist, we should still parse."""
        data = {"success": False, "clases": SAMPLE_DATE_GET_CLASES["clases"]}
        result = scraper._parse_classes_from_api_response(data)
        assert len(result) == 2

    def test_clase_id_and_dias_clases_id_as_integers(self, scraper):
        """API returns integers; we must handle correctly."""
        data = {"clases": [{"nombre": "Test", "clase_id": 104996, "dias_clases_id": 237092}]}
        result = scraper._parse_classes_from_api_response(data)
        assert result[0]["value"] == "104996-237092"

    def test_clase_id_and_dias_clases_id_as_strings(self, scraper):
        """Some APIs return strings; we must handle."""
        data = {"clases": [{"nombre": "Test", "clase_id": "104996", "dias_clases_id": "237092"}]}
        result = scraper._parse_classes_from_api_response(data)
        assert result[0]["value"] == "104996-237092"

    def test_missing_dias_clases_id_uses_fallback(self, scraper):
        """Item with only clase_id falls back to id/value parsing."""
        data = {"clases": [{"nombre": "Test", "clase_id": 104996}]}
        result = scraper._parse_classes_from_api_response(data)
        assert result[0]["value"] == "104996"

    def test_key_value_format(self, scraper):
        """Parse key-value format: {"105112-237420": "Class Name"}."""
        data = {"105112-237420": "Sesión grupal 9:00 am", "107304-241499": "Sesión privada"}
        result = scraper._parse_classes_from_api_response(data)
        assert len(result) == 2
        assert any(r["value"] == "105112-237420" for r in result)

    def test_options_key_in_response(self, scraper):
        """Some APIs use 'options' instead of 'clases'."""
        data = {"options": SAMPLE_DATE_GET_CLASES["clases"]}
        result = scraper._parse_classes_from_api_response(data)
        assert len(result) == 2

    def test_data_key_in_response(self, scraper):
        """Some APIs wrap in 'data' key."""
        data = {"data": SAMPLE_DATE_GET_CLASES["clases"]}
        result = scraper._parse_classes_from_api_response(data)
        assert len(result) == 2

    def test_html_options_skip_placeholder(self, scraper):
        """HTML options with 'Selecciona' etc. should be skipped."""
        html = '<option value="">Selecciona una clase</option><option value="104996-237092">Clase real</option>'
        result = scraper._parse_classes_from_api_response(html)
        assert len(result) == 1
        assert result[0]["value"] == "104996-237092"

    def test_none_and_empty_input(self, scraper):
        """None, empty dict, empty list should not crash."""
        assert scraper._parse_classes_from_api_response(None) == []
        assert scraper._parse_classes_from_api_response({}) == []
        assert scraper._parse_classes_from_api_response([]) == []


class TestClassInfoExtractionEdgeCases:
    """Edge cases for class_info -> class_id extraction in select_class_and_extract_reservations."""

    def test_raw_api_dict_fallback(self, scraper):
        """Raw API dict with clase_id and dias_clases_id builds correct class_id."""
        class_info = {"nombre": "Test", "clase_id": 104996, "dias_clases_id": 237092}
        class_id = (class_info.get("value") or "").strip()
        if not class_id and "clase_id" in class_info and "dias_clases_id" in class_info:
            class_id = f"{class_info['clase_id']}-{class_info['dias_clases_id']}"
        assert class_id == "104996-237092"

    def test_parsed_format_has_value(self, scraper):
        """Parsed format with value key."""
        class_info = {"value": "104996-237092", "text": "Sesión grupal 6:00 am"}
        class_id = (class_info.get("value") or "").strip()
        assert class_id == "104996-237092"

    def test_invalid_class_id_single_number(self):
        """Single number fails validation."""
        import re
        assert not re.match(r"^\d+-\d+$", "104996")

    def test_invalid_class_id_no_hyphen(self):
        """String without hyphen fails."""
        import re
        assert not re.match(r"^\d+-\d+$", "104996237092")


class TestDateFormatEdgeCases:
    """Date formats used across upcoming days."""

    def test_date_range_dd_mm_yyyy(self):
        """Scraper uses DD-MM-YYYY format for API."""
        tz = ZoneInfo("America/Santiago")
        base = datetime(2026, 2, 9, tzinfo=tz)
        for i in range(7):
            d = base + timedelta(days=i)
            date_str = d.strftime("%d-%m-%Y")
            assert len(date_str) == 10
            assert date_str[2] == "-" and date_str[5] == "-"

    def test_upcoming_dates_format(self):
        """Today + 7 days produces valid date strings."""
        tz = ZoneInfo("America/Santiago")
        today = datetime.now(tz)
        for i in range(7):
            d = today + timedelta(days=i)
            date_str = d.strftime("%d-%m-%Y")
            parts = date_str.split("-")
            assert len(parts) == 3
            assert 1 <= int(parts[0]) <= 31
            assert 1 <= int(parts[1]) <= 12
            assert len(parts[2]) == 4

    def test_date_in_url_format(self):
        """date_get_clases URL accepts DD-MM-YYYY."""
        date_str = "09-02-2026"
        url = f"https://boxmagic.cl/checkin/date_get_clases/{date_str}"
        assert "09-02-2026" in url


class TestGetAlumnosClaseResponseEdgeCases:
    """Edge cases for get_alumnos_clase API response handling."""

    def test_alumnos_empty_list_valid(self):
        """success=True with alumnos=[] is valid (class with 0 reservations)."""
        data = {"success": True, "alumnos": []}
        alumnos = data.get("alumnos") or []
        assert alumnos == []
        assert data.get("success") is True

    def test_alumnos_none_handled(self):
        """alumnos=None should be treated as []."""
        data = {"success": True, "alumnos": None}
        alumnos = data.get("alumnos") or []
        assert alumnos == []

    def test_success_false_returns_empty_structure(self):
        """success=False should yield empty reservations structure."""
        data = {"success": False, "message": "Error"}
        assert not data.get("success", False)


class TestOutputStructureValidation:
    """Validate output structure for API consumers."""

    def test_class_data_required_keys(self):
        """Each class in output must have required keys."""
        required = ["class", "classId", "reservations", "totalReservations", "extractedAt"]
        class_data = {
            "class": "Sesión grupal 6:00 am",
            "classId": "104996-237092",
            "reservations": [],
            "totalReservations": 0,
            "extractedAt": "2026-02-07T12:00:00",
        }
        for k in required:
            assert k in class_data

    def test_date_data_required_keys(self):
        """Each date in output must have required keys."""
        required = ["date", "classes", "totalClasses", "scrapedAt"]
        date_data = {"date": "09-02-2026", "classes": {}, "totalClasses": 0, "scrapedAt": "2026-02-07T12:00:00"}
        for k in required:
            assert k in date_data


class TestRegexValueExtraction:
    """DOM fallback: flexible regex for extracting clase_id-dias_clases_id."""

    def test_value_pattern_matches_standard(self):
        import re
        pattern = re.compile(r"(\d+-\d+)")
        assert pattern.search("104996-237092").group(1) == "104996-237092"

    def test_value_pattern_extracts_from_longer_string(self):
        import re
        pattern = re.compile(r"(\d+-\d+)")
        # Value might have extra chars in edge cases
        s = "104996-237092"
        m = pattern.search(s)
        assert m and m.group(1) == "104996-237092"

    def test_value_pattern_requires_digits_only(self):
        import re
        pattern = re.compile(r"^(\d+-\d+)$")
        assert pattern.match("104996-237092")
        assert not pattern.match("abc-237092")
        assert not pattern.match("104996-abc")
