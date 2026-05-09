--
-- PostgreSQL database dump
--

\restrict wZWyOkj7cAGXiptrQAs3MUwnGzlx47svIL2IKaNrpKNic4ZSxvjDz6IXUA3uEIA

-- Dumped from database version 16.12 (Debian 16.12-1.pgdg13+1)
-- Dumped by pg_dump version 16.12 (Debian 16.12-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: app_user
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2026-05-07 02:51:19.102256+00
2	contenttypes	0002_remove_content_type_name	2026-05-07 02:51:19.110302+00
3	auth	0001_initial	2026-05-07 02:51:19.183721+00
4	auth	0002_alter_permission_name_max_length	2026-05-07 02:51:19.188659+00
5	auth	0003_alter_user_email_max_length	2026-05-07 02:51:19.193352+00
6	auth	0004_alter_user_username_opts	2026-05-07 02:51:19.198505+00
7	auth	0005_alter_user_last_login_null	2026-05-07 02:51:19.205094+00
8	auth	0006_require_contenttypes_0002	2026-05-07 02:51:19.208493+00
9	auth	0007_alter_validators_add_error_messages	2026-05-07 02:51:19.217047+00
10	auth	0008_alter_user_username_max_length	2026-05-07 02:51:19.222281+00
11	auth	0009_alter_user_last_name_max_length	2026-05-07 02:51:19.227627+00
12	auth	0010_alter_group_name_max_length	2026-05-07 02:51:19.235925+00
13	auth	0011_update_proxy_permissions	2026-05-07 02:51:19.240751+00
14	auth	0012_alter_user_first_name_max_length	2026-05-07 02:51:19.248167+00
15	core	0001_initial	2026-05-07 02:51:19.922942+00
16	admin	0001_initial	2026-05-07 02:51:19.969785+00
17	admin	0002_logentry_remove_auto_add	2026-05-07 02:51:19.982847+00
18	admin	0003_logentry_add_action_flag_choices	2026-05-07 02:51:19.994882+00
19	core	0002_userprofile_shift	2026-05-07 02:51:20.009139+00
20	core	0003_scraprecord	2026-05-07 02:51:20.079085+00
21	core	0004_rename_line_process_field	2026-05-07 02:51:20.115253+00
22	core	0005_item_list_reference_image	2026-05-07 02:51:20.12675+00
23	core	0006_scraprecord_comment	2026-05-07 02:51:20.145826+00
24	core	0007_add_class_name_defectmode	2026-05-07 02:51:20.159413+00
25	core	0008_inspectionmodels_structure_and_more	2026-05-07 02:51:20.363862+00
26	core	0009_rename_structure_inspectionitem	2026-05-07 02:51:20.391741+00
27	core	0010_rename_lasted_eci_billofmaterial_latest_eci_and_more	2026-05-07 02:51:20.443847+00
28	core	0011_inspectionitem_is_exist	2026-05-07 02:51:20.455506+00
29	core	0012_remove_inspectionitem_defect_mode_and_more	2026-05-07 02:51:20.546563+00
30	core	0013_alter_item_list_sku	2026-05-07 02:51:20.563423+00
31	core	0014_alter_item_list_sd_code	2026-05-07 02:51:20.587456+00
32	core	0015_inspectionmodelsdefect	2026-05-07 02:51:20.630642+00
33	core	0016_defectmode_class_name_defectmode_inspection_model	2026-05-07 02:51:20.665065+00
34	core	0017_inspectionitem_camera_number	2026-05-07 02:51:20.673729+00
35	core	0018_inspectionmodels_count_detect	2026-05-07 02:51:20.679535+00
36	core	0019_inspectionresult	2026-05-07 02:51:20.715085+00
37	core	0020_rename_inspection_line_id_inspectionresult_inspection_line_and_more	2026-05-07 02:51:20.736427+00
38	core	0021_alter_inspectionresult_inspection_line_and_more	2026-05-07 02:51:20.753915+00
39	core	0022_inspectionresult_qr_work_and_more	2026-05-07 02:51:20.808239+00
40	core	0023_inspectionerror	2026-05-07 02:51:20.845782+00
41	core	0024_inspectionproducts	2026-05-07 02:51:20.858198+00
42	core	0025_inspectionproducts_products_patn_image	2026-05-07 02:51:20.862255+00
43	core	0026_alter_inspectionproducts_products_patn_image	2026-05-07 02:51:20.866502+00
44	core	0027_alter_inspectionproducts_products_patn_image	2026-05-07 02:51:20.871047+00
45	core	0028_rename_products_patn_image_inspectionproducts_products_path_image	2026-05-07 02:51:20.875025+00
46	sessions	0001_initial	2026-05-07 02:51:20.903491+00
47	core	0029_item_list_item_code_item_list_stage_and_more	2026-05-07 04:26:44.388287+00
48	core	0030_seed_item_stages	2026-05-07 04:26:44.422958+00
49	core	0031_remove_item_list_level	2026-05-07 05:58:55.965007+00
50	core	0032_backfill_stage_and_item_code	2026-05-07 05:58:56.671676+00
51	core	0033_reclassify_stage_by_level	2026-05-07 06:48:58.851066+00
52	core	0034_renumber_item_codes_globally	2026-05-07 07:53:07.255139+00
53	core	0035_rename_sd_code_to_sdpn	2026-05-07 08:54:10.659799+00
54	core	0036_backfill_sd_code_from_excel	2026-05-07 08:54:11.921036+00
55	core	0037_remove_item_list_sdpn	2026-05-07 09:28:36.703061+00
56	core	0038_inout_item_list_inout_plant_portion_and_more	2026-05-07 11:17:33.644032+00
57	core	0039_seed_base_lookups	2026-05-07 11:17:33.704542+00
\.


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: app_user
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 57, true);


--
-- PostgreSQL database dump complete
--

\unrestrict wZWyOkj7cAGXiptrQAs3MUwnGzlx47svIL2IKaNrpKNic4ZSxvjDz6IXUA3uEIA

