import os
import re
from html import unescape

import snowflake.connector
import torch
from dotenv import load_dotenv
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    pipeline,
)


# =========================================================
# Settings
# =========================================================

NUMBER_OF_JOBS = 500
MIN_MODEL_CONFIDENCE = 0.85
JOBBERT_MAX_TOKENS = 500

load_dotenv()


# =========================================================
# Load NLP models
# =========================================================

print("Loading JobBERT...")

skill_extractor = pipeline(
    task="token-classification",
    model="jjzha/jobbert_skill_extraction",
    aggregation_strategy="first",
    device=0 if torch.cuda.is_available() else -1,
)

print("Loading Arabic translator...")

TRANSLATION_MODEL = "Helsinki-NLP/opus-mt-ar-en"

translation_tokenizer = AutoTokenizer.from_pretrained(
    TRANSLATION_MODEL
)

translation_model = AutoModelForSeq2SeqLM.from_pretrained(
    TRANSLATION_MODEL
)


# =========================================================
# Approved skill catalog
# =========================================================

SKILL_CATALOG = [
    # Data and AI
    (
        "Natural Language Processing",
        "technical_skill",
        ["natural language processing", "nlp"],
    ),
    (
        "Machine Learning",
        "technical_skill",
        ["machine learning"],
    ),
    (
        "Deep Learning",
        "technical_skill",
        ["deep learning"],
    ),
    (
        "Artificial Intelligence",
        "technical_skill",
        ["artificial intelligence", "ai"],
    ),
    (
        "Data Engineering",
        "technical_skill",
        ["data engineering"],
    ),
    (
        "Data Analysis",
        "technical_skill",
        ["data analysis", "data analytics"],
    ),
    (
        "Data Visualization",
        "technical_skill",
        ["data visualization", "data visualisation"],
    ),
    (
        "Business Intelligence",
        "technical_skill",
        ["business intelligence"],
    ),
    (
        "Database Management",
        "technical_skill",
        ["database management"],
    ),
    (
        "ETL",
        "technical_skill",
        ["etl", "extract transform load"],
    ),

    # Data tools
    (
        "Power BI",
        "technical_skill",
        ["power bi"],
    ),
    (
        "Excel",
        "technical_skill",
        ["excel", "microsoft excel", "ms excel"],
    ),
    (
        "Tableau",
        "technical_skill",
        ["tableau"],
    ),
    (
        "Snowflake",
        "technical_skill",
        ["snowflake"],
    ),
    (
        "Airflow",
        "technical_skill",
        ["airflow", "apache airflow"],
    ),
    (
        "Apache Spark",
        "technical_skill",
        ["apache spark", "pyspark", "spark"],
    ),
    (
        "dbt",
        "technical_skill",
        ["dbt"],
    ),

    # Programming
    (
        "Python",
        "technical_skill",
        ["python"],
    ),
    (
        "SQL",
        "technical_skill",
        ["sql"],
    ),
    (
        "Java",
        "technical_skill",
        ["java"],
    ),
    (
        "JavaScript",
        "technical_skill",
        ["javascript"],
    ),
    (
        "C++",
        "technical_skill",
        ["c++"],
    ),
    (
        "C#",
        "technical_skill",
        ["c#", "c sharp"],
    ),
    (
        "Git",
        "technical_skill",
        ["git"],
    ),
    (
        "Linux",
        "technical_skill",
        ["linux"],
    ),

    # Cloud and software
    (
        "Docker",
        "technical_skill",
        ["docker"],
    ),
    (
        "Kubernetes",
        "technical_skill",
        ["kubernetes"],
    ),
    (
        "AWS",
        "technical_skill",
        ["aws", "amazon web services"],
    ),
    (
        "Microsoft Azure",
        "technical_skill",
        ["azure", "microsoft azure"],
    ),
    (
        "Google Cloud",
        "technical_skill",
        ["google cloud", "google cloud platform", "gcp"],
    ),
    (
        "Cybersecurity",
        "technical_skill",
        ["cybersecurity", "cyber security"],
    ),
    (
        "Network Administration",
        "technical_skill",
        ["network administration"],
    ),
    (
        "Software Development",
        "technical_skill",
        ["software development"],
    ),
    (
        "Web Development",
        "technical_skill",
        ["web development"],
    ),
    (
        "API Development",
        "technical_skill",
        ["api development", "rest api", "restful api"],
    ),

    # Engineering and construction
    (
        "MEP BIM Coordination",
        "technical_skill",
        ["mep bim coordination"],
    ),
    (
        "BIM",
        "technical_skill",
        ["bim", "building information modeling"],
    ),
    (
        "AutoCAD",
        "technical_skill",
        ["autocad"],
    ),
    (
        "Revit",
        "technical_skill",
        ["revit"],
    ),
    (
        "CAD",
        "technical_skill",
        ["cad", "computer aided design"],
    ),
    (
        "Quantity Surveying",
        "domain_skill",
        ["quantity surveying"],
    ),
    (
        "Construction Management",
        "domain_skill",
        ["construction management"],
    ),
    (
        "Civil Engineering",
        "domain_skill",
        ["civil engineering"],
    ),
    (
        "Mechanical Engineering",
        "domain_skill",
        ["mechanical engineering"],
    ),
    (
        "Electrical Engineering",
        "domain_skill",
        ["electrical engineering"],
    ),
    (
        "Preventive Maintenance",
        "domain_skill",
        ["preventive maintenance", "preventative maintenance"],
    ),
    (
        "Troubleshooting",
        "technical_skill",
        ["troubleshooting"],
    ),
    (
        "Occupational Health and Safety",
        "domain_skill",
        ["occupational health and safety", "hse"],
    ),

    # Business and operations
    (
        "Project Management",
        "domain_skill",
        ["project management"],
    ),
    (
        "Operations Management",
        "domain_skill",
        ["operations management"],
    ),
    (
        "Supply Chain Management",
        "domain_skill",
        ["supply chain management"],
    ),
    (
        "Inventory Management",
        "domain_skill",
        ["inventory management"],
    ),
    (
        "Vendor Management",
        "domain_skill",
        [
            "vendor management",
            "vendor relationship",
            "vendor relationships",
        ],
    ),
    (
        "Supplier Management",
        "domain_skill",
        [
            "supplier management",
            "supplier relationship",
            "supplier relationships",
        ],
    ),
    (
        "Contract Management",
        "domain_skill",
        ["contract management"],
    ),
    (
        "Procurement",
        "domain_skill",
        ["procurement", "purchasing operations"],
    ),
    (
        "Financial Analysis",
        "domain_skill",
        ["financial analysis"],
    ),
    (
        "Financial Reporting",
        "domain_skill",
        ["financial reporting"],
    ),
    (
        "Accounting",
        "domain_skill",
        ["accounting"],
    ),
    (
        "Auditing",
        "domain_skill",
        ["auditing", "audit management"],
    ),
    (
        "Budgeting",
        "domain_skill",
        ["budgeting", "budget management"],
    ),
    (
        "Risk Management",
        "domain_skill",
        ["risk management"],
    ),
    (
        "Quality Assurance",
        "domain_skill",
        ["quality assurance", "quality control"],
    ),
    (
        "Business Development",
        "domain_skill",
        ["business development"],
    ),
    (
        "Customer Relationship Management",
        "domain_skill",
        ["customer relationship management", "crm"],
    ),
    (
        "Customer Service",
        "soft_skill",
        ["customer service"],
    ),
    (
        "Digital Marketing",
        "domain_skill",
        ["digital marketing"],
    ),
    (
        "Marketing",
        "domain_skill",
        ["marketing"],
    ),
    (
        "Sales",
        "domain_skill",
        ["sales"],
    ),
    (
        "Recruitment",
        "domain_skill",
        ["recruitment", "talent acquisition"],
    ),
    (
        "Human Resources",
        "domain_skill",
        ["human resources", "hr management"],
    ),

    # Healthcare
    (
        "Clinical Research",
        "domain_skill",
        ["clinical research"],
    ),
    (
        "Medical Coding",
        "domain_skill",
        ["medical coding"],
    ),
    (
        "Patient Care",
        "domain_skill",
        ["patient care"],
    ),
    (
        "First Aid",
        "domain_skill",
        ["first aid"],
    ),
    (
        "Food Safety",
        "domain_skill",
        ["food safety"],
    ),
    (
        "Food Preparation",
        "domain_skill",
        ["food preparation"],
    ),
    (
        "Nursing",
        "domain_skill",
        ["nursing"],
    ),
    (
        "Pharmacy",
        "domain_skill",
        ["pharmacy"],
    ),
    (
        "Nutrition",
        "domain_skill",
        ["nutrition"],
    ),
    (
        "Counseling",
        "domain_skill",
        ["counseling", "counselling"],
    ),

    # Education and hospitality
    (
        "Lesson Planning",
        "domain_skill",
        ["lesson planning", "lesson plans"],
    ),
    (
        "Classroom Management",
        "domain_skill",
        ["classroom management"],
    ),
    (
        "Curriculum Development",
        "domain_skill",
        ["curriculum development"],
    ),
    (
        "Event Management",
        "domain_skill",
        ["event management"],
    ),
    (
        "Housekeeping",
        "domain_skill",
        ["housekeeping"],
    ),
    (
        "Cooking",
        "domain_skill",
        ["cooking"],
    ),

    # Soft skills
    (
        "Problem Solving",
        "soft_skill",
        ["problem solving", "problem-solving"],
    ),
    (
        "Time Management",
        "soft_skill",
        ["time management"],
    ),
    (
        "Attention to Detail",
        "soft_skill",
        ["attention to detail"],
    ),
    (
        "Interpersonal Skills",
        "soft_skill",
        ["interpersonal skill", "interpersonal skills"],
    ),
    (
        "Critical Thinking",
        "soft_skill",
        ["critical thinking"],
    ),
    (
        "Decision Making",
        "soft_skill",
        ["decision making", "decision-making"],
    ),
    (
        "Presentation Skills",
        "soft_skill",
        ["presentation skill", "presentation skills"],
    ),
    (
        "Organizational Skills",
        "soft_skill",
        [
            "organizational skill",
            "organizational skills",
            "organisation skills",
        ],
    ),
    (
        "Communication",
        "soft_skill",
        ["communication", "communication skills"],
    ),
    (
        "Teamwork",
        "soft_skill",
        ["teamwork", "team work"],
    ),
    (
        "Leadership",
        "soft_skill",
        ["leadership"],
    ),
    (
        "Adaptability",
        "soft_skill",
        ["adaptability"],
    ),
    (
        "Negotiation",
        "soft_skill",
        ["negotiation"],
    ),
    (
        "Planning",
        "soft_skill",
        ["planning skills"],
    ),

    # Languages
    (
        "Arabic",
        "language_skill",
        ["arabic language", "fluent in arabic"],
    ),
    (
        "English",
        "language_skill",
        [
            "english language",
            "fluent in english",
            "english proficiency",
        ],
    ),
    (
        "French",
        "language_skill",
        ["french language", "fluent in french"],
    ),
]


# =========================================================
# Build safe search patterns
# =========================================================

COMPILED_SKILL_CATALOG = []

for skill_name, skill_category, aliases in SKILL_CATALOG:
    compiled_aliases = []

    for alias in aliases:
        pattern = (
            r"(?<!\w)"
            + re.escape(alias)
            + r"(?!\w)"
        )

        compiled_aliases.append(
            re.compile(
                pattern,
                re.IGNORECASE,
            )
        )

    COMPILED_SKILL_CATALOG.append(
        (
            skill_name,
            skill_category,
            compiled_aliases,
        )
    )


# =========================================================
# Text functions
# =========================================================

def normalize_text(text):
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_arabic(text):
    return bool(
        re.search(
            r"[\u0600-\u06FF]",
            text or "",
        )
    )


def translate_to_english(text):
    inputs = translation_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )

    with torch.no_grad():
        translated_tokens = translation_model.generate(
            **inputs,
            max_length=512,
        )

    return translation_tokenizer.decode(
        translated_tokens[0],
        skip_special_tokens=True,
    )


def prepare_text_for_jobbert(text):
    encoded_text = skill_extractor.tokenizer(
        text,
        truncation=True,
        max_length=JOBBERT_MAX_TOKENS,
        add_special_tokens=True,
    )

    safe_text = skill_extractor.tokenizer.decode(
        encoded_text["input_ids"],
        skip_special_tokens=True,
    )

    return safe_text


def clean_candidate(value):
    value = unescape(value or "")
    value = value.replace("##", "")
    value = re.sub(r"\s+", " ", value)

    return value.strip(
        " \n\t,.;:!?()[]{}-_/&"
    )


def add_skill(
    output,
    seen,
    skill_name,
    skill_category,
    confidence,
    evidence,
):
    skill_key = skill_name.casefold()

    if skill_key in seen:
        return

    seen.add(skill_key)

    output.append(
        {
            "skill_name": skill_name,
            "skill_category": skill_category,
            "confidence": round(
                float(confidence),
                3,
            ),
            "evidence_span": evidence[:500],
        }
    )


def find_catalog_skill(text):
    for (
        skill_name,
        skill_category,
        aliases,
    ) in COMPILED_SKILL_CATALOG:

        for alias_pattern in aliases:
            match = alias_pattern.search(text)

            if match:
                return (
                    skill_name,
                    skill_category,
                    match.group(0),
                )

    return None


# =========================================================
# Extract skills
# =========================================================

def extract_skills(description):
    original_text = normalize_text(description)

    if not original_text:
        return []

    language = (
        "Arabic"
        if contains_arabic(original_text)
        else "English"
    )

    if language == "Arabic":
        text_for_model = translate_to_english(
            original_text
        )

        arabic_evidence = original_text[:500]

    else:
        text_for_model = original_text
        arabic_evidence = ""

    text_for_model = normalize_text(
        text_for_model
    )

    safe_text_for_jobbert = prepare_text_for_jobbert(
        text_for_model
    )

    output = []
    seen = set()

    # JobBERT model extraction
    raw_results = skill_extractor(
        safe_text_for_jobbert
    )

    for result in raw_results:
        confidence = float(
            result.get("score", 0)
        )

        if confidence < MIN_MODEL_CONFIDENCE:
            continue

        candidate = clean_candidate(
            result.get("word", "")
        )

        if not candidate:
            continue

        catalog_result = find_catalog_skill(
            candidate
        )

        if not catalog_result:
            continue

        (
            skill_name,
            skill_category,
            matched_text,
        ) = catalog_result

        evidence = (
            arabic_evidence
            if language == "Arabic"
            else matched_text
        )

        add_skill(
            output=output,
            seen=seen,
            skill_name=skill_name,
            skill_category=skill_category,
            confidence=confidence,
            evidence=evidence,
        )

    # Recover explicit skills that JobBERT missed
    for (
        skill_name,
        skill_category,
        aliases,
    ) in COMPILED_SKILL_CATALOG:

        for alias_pattern in aliases:
            match = alias_pattern.search(
                text_for_model
            )

            if not match:
                continue

            evidence = (
                arabic_evidence
                if language == "Arabic"
                else match.group(0)
            )

            add_skill(
                output=output,
                seen=seen,
                skill_name=skill_name,
                skill_category=skill_category,
                confidence=1.0,
                evidence=evidence,
            )

            break

    return output


# =========================================================
# Snowflake connection
# =========================================================

connection = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role=os.getenv(
        "SNOWFLAKE_ROLE",
        "JOBPULSE_DEVELOPER",
    ),
    warehouse=os.getenv(
        "SNOWFLAKE_WAREHOUSE",
        "JOBPULSE_WH",
    ),
    database=os.getenv(
        "SNOWFLAKE_DATABASE",
        "JOBPULSE_DB",
    ),
    schema=os.getenv(
        "SNOWFLAKE_SCHEMA",
        "RAW",
    ),
    autocommit=False,
)

cursor = connection.cursor()


# =========================================================
# Process jobs incrementally in batches
# =========================================================

try:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS
        JOBPULSE_DB.RAW.SKILL_EXTRACTION_LOG (
            job_key VARCHAR NOT NULL,
            processed_at TIMESTAMP_NTZ
                DEFAULT CURRENT_TIMESTAMP(),
            skill_count INTEGER,
            status VARCHAR
        )
        """
    )

    connection.commit()

    total_inserted = 0
    total_errors = 0
    total_processed = 0
    batch_number = 0

    # =====================================================
    # Keep processing batches until no jobs remain
    # =====================================================

    while True:

        batch_number += 1

        cursor.execute(
            f"""
            WITH unique_jobs AS (
                SELECT
                    job_key,
                    description
                FROM JOBPULSE_DB.SILVER.INT_JOBS_FINAL
                WHERE description IS NOT NULL
                  AND TRIM(description) <> ''

                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY job_key
                    ORDER BY job_key
                ) = 1
            )

            SELECT
                jobs.job_key,
                jobs.description
            FROM unique_jobs AS jobs

            WHERE NOT EXISTS (
                SELECT 1
                FROM JOBPULSE_DB.RAW.EXTRACTED_SKILLS
                    AS skills
                WHERE skills.job_key = jobs.job_key
            )

            AND NOT EXISTS (
                SELECT 1
                FROM JOBPULSE_DB.RAW.SKILL_EXTRACTION_LOG
                    AS extraction_log
                WHERE extraction_log.job_key =
                      jobs.job_key

                  AND extraction_log.status IN (
                      'skills_found',
                      'no_skills_found'
                  )
            )

            ORDER BY jobs.job_key

            LIMIT {NUMBER_OF_JOBS}
            """
        )

        jobs = cursor.fetchall()

        # -------------------------------------------------
        # Stop when there are no more unprocessed jobs
        # -------------------------------------------------

        if not jobs:
            print(
                "\n========================================"
            )
            print(
                "No more unprocessed jobs."
            )
            print(
                "All available jobs have been processed."
            )
            print(
                "========================================\n"
            )
            break

        print(
            "\n========================================"
        )
        print(
            f"Starting batch {batch_number}"
        )
        print(
            f"Loaded {len(jobs)} jobs for processing."
        )
        print(
            "========================================\n"
        )

        # -------------------------------------------------
        # Process current batch
        # -------------------------------------------------

        for job_number, (
            job_key,
            description,
        ) in enumerate(
            jobs,
            start=1,
        ):

            print(
                f"Processing job "
                f"{job_number}/{len(jobs)}: "
                f"{job_key}"
            )

            try:
                skills = extract_skills(
                    description
                )

                if skills:

                    rows_to_insert = [
                        (
                            job_key,
                            skill["skill_name"],
                            skill["skill_category"],
                            skill["confidence"],
                            skill["evidence_span"],
                        )
                        for skill in skills
                    ]

                    cursor.executemany(
                        """
                        INSERT INTO
                        JOBPULSE_DB.RAW.EXTRACTED_SKILLS (
                            job_key,
                            skill_name,
                            skill_category,
                            confidence,
                            evidence_span
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        rows_to_insert,
                    )

                    skill_count = len(
                        rows_to_insert
                    )

                    status = "skills_found"

                    total_inserted += skill_count

                    print(
                        f"Inserted "
                        f"{skill_count} skills."
                    )

                else:
                    skill_count = 0
                    status = "no_skills_found"

                    print(
                        "No approved skills found."
                    )

                # -----------------------------------------
                # Log successful processing
                # -----------------------------------------

                cursor.execute(
                    """
                    INSERT INTO
                    JOBPULSE_DB.RAW.SKILL_EXTRACTION_LOG (
                        job_key,
                        skill_count,
                        status
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        job_key,
                        skill_count,
                        status,
                    ),
                )

                # Save after every job
                connection.commit()

                total_processed += 1

            except Exception as job_error:

                connection.rollback()

                total_errors += 1

                print(
                    f"Skipped job because of error: "
                    f"{job_error}"
                )

                # -----------------------------------------
                # Log failed job
                #
                # IMPORTANT:
                # status = error means this job is NOT
                # considered successfully processed.
                # Therefore it can be retried in a future
                # run.
                # -----------------------------------------

                cursor.execute(
                    """
                    INSERT INTO
                    JOBPULSE_DB.RAW.SKILL_EXTRACTION_LOG (
                        job_key,
                        skill_count,
                        status
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        job_key,
                        0,
                        "error",
                    ),
                )

                connection.commit()

                continue

        print(
            "\n----------------------------------------"
        )
        print(
            f"Batch {batch_number} completed."
        )
        print(
            f"Jobs processed so far: "
            f"{total_processed}"
        )
        print(
            f"Total inserted skills: "
            f"{total_inserted}"
        )
        print(
            f"Total job errors: "
            f"{total_errors}"
        )
        print(
            "----------------------------------------\n"
        )

        # The while loop now starts another query.
        # The next query will automatically exclude
        # jobs already processed in this batch.


    # =====================================================
    # Final summary
    # =====================================================

    print(
        "\n========================================"
    )
    print(
        "Finished successfully."
    )
    print(
        f"Total batches: {batch_number}"
    )
    print(
        f"Total jobs processed: {total_processed}"
    )
    print(
        f"Total inserted skills: {total_inserted}"
    )
    print(
        f"Jobs skipped because of errors: {total_errors}"
    )
    print(
        "========================================"
    )


except Exception as error:

    connection.rollback()

    print(
        f"\nFatal error: {error}"
    )

    raise

finally:

    cursor.close()
    connection.close()

