-- Rename four existing judges to surnames + add Newton (Phase 3) scaffold
-- SKEPTIC  -> BALDWIN (critic):    James Baldwin
-- ETHICIST -> MURRAY  (ethicist):  Pauli Murray
-- BUILDER  -> RUSTIN  (builder):   Bayard Rustin
-- SYLVIA   -> RIVERA  (inclusion): Sylvia Rivera
-- NEW: NEWTON (collaborator, Phase 3): Huey P. Newton — columns nullable; unused until Phase 3

ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN skeptic_response  TO baldwin_response;
ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN ethicist_response TO murray_response;
ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN builder_response  TO rustin_response;
ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN sylvia_response   TO rivera_response;

ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN skeptic_recommendation  TO baldwin_recommendation;
ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN ethicist_recommendation TO murray_recommendation;
ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN builder_recommendation  TO rustin_recommendation;
ALTER TABLE public.dreamcatcher_verdicts RENAME COLUMN sylvia_recommendation   TO rivera_recommendation;

ALTER TABLE public.dreamcatcher_verdicts ADD COLUMN newton_response       text NULL;
ALTER TABLE public.dreamcatcher_verdicts ADD COLUMN newton_recommendation text NULL;
