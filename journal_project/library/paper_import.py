import json
import unicodedata
from dataclasses import dataclass
from typing import Any, BinaryIO, Mapping, Sequence

from django.core.exceptions import ValidationError

from .models import KnowledgeItem
from .services import create_paper


class PaperImportFileError(ValueError):
    """Raised when an uploaded file is not valid paper-manager JSON."""


class PaperImportRecordError(ValueError):
    """Raised when one paper-manager record cannot be imported."""


@dataclass(frozen=True)
class InvalidPaperRecord:
    """Describe one rejected record using its one-based file position."""

    record_number: int
    reason: str


@dataclass(frozen=True)
class PaperImportResult:
    """Summarize one independently processed paper JSON upload."""

    imported: int
    skipped_duplicates: int
    invalid_records: tuple[InvalidPaperRecord, ...]

    @property
    def invalid(self) -> int:
        """Return the number of rejected records."""
        return len(self.invalid_records)


PaperFingerprint = tuple[str, int | None, str]


def normalize_fingerprint_text(value: str) -> str:
    """Normalize case, whitespace, and punctuation for duplicate matching."""
    normalized = unicodedata.normalize('NFKC', value).casefold()
    punctuation_normalized = ''.join(
        ' ' if unicodedata.category(character).startswith('P') else character
        for character in normalized
    )
    return ' '.join(punctuation_normalized.split())


def paper_fingerprint(
    *,
    title: str,
    publication_year: int | None,
    authors: str,
) -> PaperFingerprint:
    """Return the normalized title, year, and author duplicate key."""
    return (
        normalize_fingerprint_text(title),
        publication_year,
        normalize_fingerprint_text(authors),
    )


def load_paper_manager_json(uploaded_file: BinaryIO) -> list[Any]:
    """Decode an uploaded UTF-8 JSON file containing a list of records."""
    try:
        contents = uploaded_file.read()
        if isinstance(contents, bytes):
            decoded = contents.decode('utf-8-sig')
        else:
            decoded = contents
        records = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise PaperImportFileError('Upload a valid UTF-8 JSON file.') from error

    if not isinstance(records, list):
        raise PaperImportFileError(
            'The JSON file must contain a list of paper records.'
        )
    return records


def parse_paper_record(record: Any) -> dict[str, Any]:
    """Validate and map one paper-manager record to paper service fields."""
    if not isinstance(record, Mapping):
        raise PaperImportRecordError('record must be a JSON object')

    title = _required_title(record.get('title'))
    publication_year = _publication_year(record.get('year'))
    return {
        'title': title,
        'authors': _optional_text(record.get('authors'), 'authors'),
        'publication_year': publication_year,
        'status': KnowledgeItem.Status.QUEUED,
        'summary': '',
        'source_url': '',
        'journal': '',
        'doi': '',
        'asset_class': _optional_text(record.get('asset class'), 'asset class'),
        'sample_size_data_source': _optional_text(
            record.get('sample size, data and source'),
            'sample size, data and source',
        ),
        'methodology_research_design': _optional_text(
            record.get('methodology and research design'),
            'methodology and research design',
        ),
        'key_research_question': _optional_text(
            record.get('key research question'),
            'key research question',
        ),
        'key_findings_practical_applications': _optional_text(
            record.get('key findings and practical applications'),
            'key findings and practical applications',
        ),
    }


def import_paper_records(*, user: Any, records: Sequence[Any]) -> PaperImportResult:
    """Import valid unique records without mutating existing user papers."""
    fingerprints = _existing_paper_fingerprints(user)
    invalid_records: list[InvalidPaperRecord] = []
    imported = 0
    skipped_duplicates = 0

    for record_number, record in enumerate(records, start=1):
        try:
            paper_data = parse_paper_record(record)
        except PaperImportRecordError as error:
            invalid_records.append(
                InvalidPaperRecord(record_number, str(error))
            )
            continue

        fingerprint = paper_fingerprint(
            title=paper_data['title'],
            publication_year=paper_data['publication_year'],
            authors=paper_data['authors'],
        )
        if fingerprint in fingerprints:
            skipped_duplicates += 1
            continue

        try:
            create_paper(user=user, data=paper_data)
        except ValidationError as error:
            invalid_records.append(
                InvalidPaperRecord(
                    record_number,
                    '; '.join(error.messages),
                )
            )
            continue

        fingerprints.add(fingerprint)
        imported += 1

    return PaperImportResult(
        imported=imported,
        skipped_duplicates=skipped_duplicates,
        invalid_records=tuple(invalid_records),
    )


def _existing_paper_fingerprints(user: Any) -> set[PaperFingerprint]:
    """Return duplicate keys for only the current user's stored papers."""
    stored_fields = KnowledgeItem.objects.filter(
        user=user,
        source_type=KnowledgeItem.SourceType.PAPER,
    ).values_list('title', 'paper_detail__publication_year', 'creator')
    return {
        paper_fingerprint(
            title=title,
            publication_year=publication_year,
            authors=authors,
        )
        for title, publication_year, authors in stored_fields
    }


def _required_title(value: Any) -> str:
    """Return a clean usable title or reject the record."""
    if not isinstance(value, str) or not value.strip():
        raise PaperImportRecordError('missing title')
    return ' '.join(value.split())


def _optional_text(value: Any, field_name: str) -> str:
    """Return a stripped optional string or reject an invalid JSON value."""
    if value is None:
        return ''
    if not isinstance(value, str):
        raise PaperImportRecordError(f'invalid {field_name}')
    return value.strip()


def _publication_year(value: Any) -> int | None:
    """Normalize missing and zero years while rejecting other invalid values."""
    if value in (None, '', 0, '0'):
        return None
    if isinstance(value, bool):
        raise PaperImportRecordError('invalid year')
    if isinstance(value, int):
        year = value
    elif isinstance(value, str) and value.strip().isdigit():
        year = int(value.strip())
    else:
        raise PaperImportRecordError('invalid year')
    if year <= 0:
        raise PaperImportRecordError('invalid year')
    return year
