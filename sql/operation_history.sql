-- Independent Waterbe operational history. No business-table mutation.
BEGIN;
CREATE TABLE IF NOT EXISTS public.waterbe_operation_history (
  sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source text NOT NULL, event_id text NOT NULL,
  store text, feature text NOT NULL, target text NOT NULL, operation_id text,
  kind text NOT NULL, result text NOT NULL, observed_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  body jsonb NOT NULL, UNIQUE(source,event_id)
);
CREATE INDEX IF NOT EXISTS waterbe_history_lookup ON public.waterbe_operation_history(store,feature,observed_at);
CREATE INDEX IF NOT EXISTS waterbe_history_operation ON public.waterbe_operation_history(operation_id);
ALTER TABLE public.waterbe_operation_history ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.waterbe_operation_history FROM anon,authenticated;
GRANT SELECT ON public.waterbe_operation_history TO service_role;
CREATE OR REPLACE FUNCTION public.waterbe_history_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=public AS $$
BEGIN RAISE EXCEPTION 'append_only'; END $$;
DROP TRIGGER IF EXISTS waterbe_history_immutable ON public.waterbe_operation_history;
CREATE TRIGGER waterbe_history_immutable BEFORE UPDATE OR DELETE ON public.waterbe_operation_history
FOR EACH ROW EXECUTE FUNCTION public.waterbe_history_immutable();
CREATE OR REPLACE FUNCTION public.append_waterbe_history(p_event jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE previous jsonb; inserted_sequence bigint;
BEGIN
  IF jsonb_typeof(p_event) <> 'object' OR octet_length(p_event::text)>65536
     OR EXISTS(SELECT 1 FROM jsonb_object_keys(p_event) k WHERE k NOT IN
       ('event_id','source','kind','result','feature','target','store','operation_id','occurred_at',
        'last_confirmed_at','observed_at','actor','route','rule_version','changes','evidence_ids'))
     OR NOT (p_event ?& ARRAY['event_id','source','kind','result','feature','target','observed_at'])
     OR p_event->>'source' NOT IN ('seacode','caspi','cas_central','namseon_sales','daeyoung_sales','waterbe','deployment')
     OR p_event->>'kind' NOT IN ('request','result','observation','change','incident','recovery')
     OR p_event->>'result' NOT IN ('pending','succeeded','failed','uncertain','observed') THEN
    RAISE EXCEPTION 'invalid_event';
  END IF;
  INSERT INTO public.waterbe_operation_history(source,event_id,store,feature,target,operation_id,kind,result,observed_at,body)
  VALUES(p_event->>'source',p_event->>'event_id',p_event->>'store',p_event->>'feature',p_event->>'target',
    p_event->>'operation_id',p_event->>'kind',p_event->>'result',(p_event->>'observed_at')::timestamptz,p_event)
  ON CONFLICT(source,event_id) DO NOTHING RETURNING sequence INTO inserted_sequence;
  IF inserted_sequence IS NULL THEN
    SELECT body,sequence INTO previous,inserted_sequence FROM public.waterbe_operation_history
      WHERE source=p_event->>'source' AND event_id=p_event->>'event_id';
    IF previous IS DISTINCT FROM p_event THEN RAISE EXCEPTION 'event_identity_conflict'; END IF;
    RETURN jsonb_build_object('status','duplicate','sequence',inserted_sequence);
  END IF;
  RETURN jsonb_build_object('status','stored','sequence',inserted_sequence);
END $$;
REVOKE ALL ON FUNCTION public.append_waterbe_history(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.append_waterbe_history(jsonb) TO service_role;
REVOKE ALL ON FUNCTION public.waterbe_history_immutable() FROM PUBLIC,anon,authenticated;
CREATE OR REPLACE FUNCTION public.append_waterbe_history_batch(p_events jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE event jsonb; results jsonb='[]'::jsonb; ack jsonb;
BEGIN
  IF jsonb_typeof(p_events)<>'array' OR jsonb_array_length(p_events)>500 THEN RAISE EXCEPTION 'invalid_batch'; END IF;
  FOR event IN SELECT value FROM jsonb_array_elements(p_events) LOOP
    BEGIN
      ack=public.append_waterbe_history(event);
      results=results || jsonb_build_array(ack || jsonb_build_object('event_id',event->>'event_id','source',event->>'source'));
    EXCEPTION WHEN OTHERS THEN
      results=results || jsonb_build_array(jsonb_build_object('status','rejected','event_id',event->>'event_id','source',event->>'source'));
    END;
  END LOOP;
  RETURN results;
END $$;
REVOKE ALL ON FUNCTION public.append_waterbe_history_batch(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.append_waterbe_history_batch(jsonb) TO service_role;
CREATE TABLE IF NOT EXISTS public.waterbe_history_worker_status (
  id text PRIMARY KEY, checked_at timestamptz NOT NULL DEFAULT now(), body jsonb NOT NULL
);
ALTER TABLE public.waterbe_history_worker_status ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.waterbe_history_worker_status FROM anon,authenticated;
GRANT SELECT ON public.waterbe_history_worker_status TO service_role;
CREATE OR REPLACE FUNCTION public.set_waterbe_history_status(p_status jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
BEGIN
  IF jsonb_typeof(p_status)<>'object' OR octet_length(p_status::text)>65536 THEN RAISE EXCEPTION 'invalid_status'; END IF;
  INSERT INTO public.waterbe_history_worker_status(id,body) VALUES('central',p_status)
  ON CONFLICT(id) DO UPDATE SET body=excluded.body,checked_at=now();
  RETURN jsonb_build_object('status','stored');
END $$;
REVOKE ALL ON FUNCTION public.set_waterbe_history_status(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.set_waterbe_history_status(jsonb) TO service_role;
GRANT SELECT ON public.products_wangsimni,public.products_mapo,public.products_mia,
  public.products_wolgye,public.scale_text_snapshots,public.caspi_operation_receipts TO service_role;
COMMIT;
