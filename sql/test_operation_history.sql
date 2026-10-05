BEGIN;
DO $$
DECLARE e jsonb; a jsonb; b jsonb;
BEGIN
 e='{"source":"waterbe","event_id":"transactional-test","kind":"observation","result":"observed","feature":"test","target":"test","observed_at":"2026-10-05T00:00:00Z"}'::jsonb;
 a=public.append_waterbe_history(e);
 b=public.append_waterbe_history(e);
 IF a->>'status'<>'stored' OR b->>'status'<>'duplicate' THEN RAISE EXCEPTION 'dedup test failed'; END IF;
 BEGIN
   PERFORM public.append_waterbe_history(e || '{"target":"different"}'::jsonb);
   RAISE EXCEPTION 'conflict accepted';
 EXCEPTION WHEN OTHERS THEN
   IF SQLERRM<>'event_identity_conflict' THEN RAISE; END IF;
 END;
 BEGIN
   UPDATE public.waterbe_operation_history SET target='different' WHERE event_id='transactional-test';
   RAISE EXCEPTION 'update accepted';
 EXCEPTION WHEN OTHERS THEN
   IF SQLERRM<>'append_only' THEN RAISE; END IF;
 END;
 IF has_table_privilege('anon','public.waterbe_operation_history','SELECT') OR
    has_function_privilege('anon','public.append_waterbe_history(jsonb)','EXECUTE') OR
    has_function_privilege('authenticated','public.append_waterbe_history(jsonb)','EXECUTE') THEN
   RAISE EXCEPTION 'client privilege leak';
 END IF;
END $$;
ROLLBACK;
SELECT 'dedup/conflict/immutable/client-denial verified; test rows rolled back' AS result;
