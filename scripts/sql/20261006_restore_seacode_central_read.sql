-- Approved central read repair. No app-role, RLS, data or scale changes.
BEGIN;
DO $repair$
DECLARE target record;
BEGIN
  FOR target IN
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
      AND (tablename = 'product_scale_sync_bindings'
        OR tablename ~ '^(ingredients|product_ingredients|product_quality|recipes|recipe_ingredients)_(mapo|mia|wangsimni|wolgye|mooner)$')
  LOOP
    EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', target.tablename);
  END LOOP;
END $repair$;
COMMIT;
