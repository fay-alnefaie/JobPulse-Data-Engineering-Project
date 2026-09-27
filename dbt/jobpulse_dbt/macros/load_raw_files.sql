{% macro load_raw_files() %}

    {% set sql %}
        copy into {{ target.database }}.RAW.JOBS_RAW
        from @jobpulse_azure_stage
        file_format = (format_name = 'jobpulse_csv_format')
        on_error = 'continue'
    {% endset %}

    {% do run_query(sql) %}
    {% do log("COPY INTO completed for RAW.JOBS_RAW", info=True) %}

{% endmacro %}