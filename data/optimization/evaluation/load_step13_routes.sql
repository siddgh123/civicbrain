-- ================================================================
-- CIVICBRAIN STEP 13 - LOAD FINAL ROUTES
-- Source: final_step13_route_audit.csv
-- Final routes: 109
-- Final routed jobs: 238
-- ================================================================

BEGIN;

TRUNCATE TABLE
    step13_route_stops,
    step13_routes
RESTART IDENTITY;

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-09-28', 10.5022, 0.343806, 7.9, 8.243806, '16:14', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (1, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (1, 1, 'JOB', '152', 18.720076, 73.691013, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (1, 2, 'JOB', '355', 18.733856, 73.678655, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (1, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-09-29', 7.7716, 0.233917, 8.3, 8.533917, '16:32', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (2, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (2, 1, 'JOB', '252', 18.743836, 73.692451, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (2, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-09-30', 6.0392, 0.194111, 7.4, 7.594111, '15:35', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (3, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (3, 1, 'JOB', '217', 18.746813, 73.703666, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (3, 2, 'JOB', '124', 18.74699, 73.696762, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (3, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-01', 6.9198, 0.251778, 8.5, 8.751778, '16:45', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (4, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (4, 1, 'JOB', '92', 18.734711, 73.6725, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (4, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-02', 3.9333, 0.0985, 8.8, 8.8985, '16:53', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (5, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (5, 1, 'JOB', '321', 18.713971, 73.695705, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (5, 2, 'JOB', '55', 18.716675, 73.696687, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (5, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-03', 6.7933, 0.247, 8.0, 8.247, '16:14', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (6, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (6, 1, 'JOB', '377', 18.737665, 73.674577, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (6, 2, 'JOB', '65', 18.736449, 73.677324, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (6, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-04', 3.6866, 0.144722, 8.4, 8.544722, '16:32', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (7, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (7, 1, 'JOB', '408', 18.736685, 73.687945, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (7, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-05', 7.5688, 0.281222, 8.7, 8.981222, '16:58', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (8, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (8, 1, 'JOB', '350', 18.736736, 73.676131, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (8, 2, 'JOB', '313', 18.737786, 73.670608, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (8, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-06', 3.9996, 0.128583, 7.7, 7.828583, '15:49', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (9, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (9, 1, 'JOB', '61', 18.734918, 73.69246, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (9, 2, 'JOB', '214', 18.734994, 73.691938, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (9, 3, 'JOB', '169', 18.74267, 73.695497, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (9, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-07', 3.3379, 0.163472, 6.9, 7.063472, '15:03', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (10, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (10, 1, 'JOB', '316', 18.74364, 73.706013, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (10, 2, 'JOB', '487', 18.741241, 73.702786, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (10, 3, 'JOB', '259', 18.73777, 73.705226, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (10, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-08', 9.6921, 0.2855, 7.8, 8.0855, '16:05', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (11, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (11, 1, 'JOB', '305', 18.732865, 73.663938, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (11, 2, 'JOB', '460', 18.732962, 73.658433, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (11, 3, 'JOB', '205', 18.732646, 73.658627, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (11, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-09', 12.5317, 0.353139, 8.2, 8.553139, '16:33', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (12, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (12, 1, 'JOB', '388', 18.734758, 73.663541, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (12, 2, 'JOB', '346', 18.72277, 73.666863, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (12, 3, 'JOB', '76', 18.726137, 73.672496, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (12, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-10', 0.8912, 0.031778, 3.6, 3.631778, '11:37', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (13, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (13, 1, 'JOB', '32', 18.72794, 73.701457, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (13, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-11', 13.4375, 0.456944, 8.3, 8.756944, '16:45', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (14, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (14, 1, 'JOB', '202', 18.747017, 73.683807, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (14, 2, 'JOB', '416', 18.749503, 73.677009, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (14, 3, 'JOB', '136', 18.741266, 73.66995, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (14, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-12', 10.6288, 0.371361, 8.4, 8.771361, '16:46', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (15, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (15, 1, 'JOB', '34', 18.724295, 73.678754, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (15, 2, 'JOB', '461', 18.716401, 73.688861, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (15, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-13', 11.817, 0.423917, 7.7, 8.123917, '16:07', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (16, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (16, 1, 'JOB', '10', 18.708357, 73.704338, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (16, 2, 'JOB', '314', 18.711431, 73.705318, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (16, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-14', 12.7468, 0.412083, 8.4, 8.812083, '16:48', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (17, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (17, 1, 'JOB', '26', 18.748202, 73.705266, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (17, 2, 'JOB', '253', 18.732826, 73.70326, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (17, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-15', 3.824, 0.112472, 8.8, 8.912472, '16:54', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (18, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (18, 1, 'JOB', '370', 18.728417, 73.692983, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (18, 2, 'JOB', '70', 18.720577, 73.697461, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (18, 3, 'JOB', '457', 18.719411, 73.701194, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (18, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-16', 8.9497, 0.327, 8.6, 8.927, '16:55', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (19, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (19, 1, 'JOB', '466', 18.744007, 73.673671, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (19, 2, 'JOB', '260', 18.735682, 73.681755, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (19, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-17', 15.0649, 0.441194, 8.4, 8.841194, '16:50', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (20, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (20, 1, 'JOB', '481', 18.710476, 73.684758, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (20, 2, 'JOB', '50', 18.705376, 73.683264, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (20, 3, 'JOB', '298', 18.721417, 73.680125, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (20, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-18', 12.9539, 0.452472, 8.0, 8.452472, '16:27', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (21, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (21, 1, 'JOB', '343', 18.706066, 73.70975, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (21, 2, 'JOB', '154', 18.713807, 73.705051, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (21, 3, 'JOB', '349', 18.711956, 73.710104, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (21, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-19', 14.5637, 0.452806, 8.5, 8.952806, '16:57', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (22, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (22, 1, 'JOB', '418', 18.735617, 73.6656, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (22, 2, 'JOB', '304', 18.726263, 73.655896, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (22, 3, 'JOB', '335', 18.723714, 73.675482, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (22, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-20', 13.6874, 0.308306, 8.5, 8.808306, '16:48', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (23, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (23, 1, 'JOB', '164', 18.714268, 73.701396, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (23, 2, 'JOB', '110', 18.705887, 73.684354, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (23, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-21', 15.0042, 0.3725, 7.7, 8.0725, '16:04', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (24, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (24, 1, 'JOB', '328', 18.70937, 73.687442, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (24, 2, 'JOB', '25', 18.710346, 73.688156, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (24, 3, 'JOB', '376', 18.705033, 73.694657, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (24, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-22', 12.1987, 0.325667, 8.2, 8.525667, '16:31', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (25, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (25, 1, 'JOB', '365', 18.700704, 73.696903, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (25, 2, 'JOB', '146', 18.699035, 73.702324, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (25, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-23', 10.4875, 0.377722, 8.5, 8.877722, '16:52', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (26, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (26, 1, 'JOB', '185', 18.709222, 73.705618, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (26, 2, 'JOB', '440', 18.709747, 73.706284, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (26, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-24', 9.0802, 0.28875, 8.1, 8.38875, '16:23', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (27, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (27, 1, 'JOB', '347', 18.74234, 73.679605, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (27, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-25', 14.5683, 0.426417, 8.4, 8.826417, '16:49', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (28, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (28, 1, 'JOB', '409', 18.719144, 73.681534, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (28, 2, 'JOB', '424', 18.712375, 73.694069, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (28, 3, 'JOB', '130', 18.710461, 73.688789, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (28, 4, 'JOB', '463', 18.706996, 73.690635, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (28, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-26', 9.101, 0.249917, 7.3, 7.549917, '15:32', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (29, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (29, 1, 'JOB', '31', 18.700823, 73.707249, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (29, 2, 'JOB', '277', 18.69802, 73.70995, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (29, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T001', '2026-10-27', 5.1144, 0.20025, 8.2, 8.40025, '16:24', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (30, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (30, 1, 'JOB', '181', 18.743123, 73.690776, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (30, 2, 'JOB', '425', 18.732505, 73.690148, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (30, 3, 'JOB', '40', 18.729828, 73.699809, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (30, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-09-28', 14.1959, 0.421583, 8.4, 8.821583, '16:49', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (31, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (31, 1, 'JOB', '280', 18.715782, 73.687706, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (31, 2, 'JOB', '490', 18.709493, 73.694733, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (31, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-09-29', 3.2258, 0.1225, 7.7, 7.8225, '15:49', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (32, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (32, 1, 'JOB', '331', 18.734042, 73.691523, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (32, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-09-30', 14.0139, 0.448861, 7.3, 7.748861, '15:44', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (33, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (33, 1, 'JOB', '484', 18.750341, 73.708686, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (33, 2, 'JOB', '319', 18.74585, 73.705545, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (33, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-01', 12.3113, 0.31075, 8.6, 8.91075, '16:54', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (34, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (34, 1, 'JOB', '413', 18.722609, 73.66348, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (34, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-02', 8.1461, 0.256056, 8.6, 8.856056, '16:51', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (35, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (35, 1, 'JOB', '311', 18.72078, 73.684391, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (35, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-03', 18.3634, 0.533917, 7.7, 8.233917, '16:14', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (36, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (36, 1, 'JOB', '485', 18.727475, 73.688187, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (36, 2, 'JOB', '262', 18.712541, 73.710954, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (36, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-04', 3.312, 0.123, 8.4, 8.523, '16:31', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (37, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (37, 1, 'JOB', '188', 18.732166, 73.690273, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (37, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-05', 12.0152, 0.387167, 8.5, 8.887167, '16:53', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (38, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (38, 1, 'JOB', '86', 18.714932, 73.707336, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (38, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-06', 22.9887, 0.618083, 6.9, 7.518083, '15:31', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (39, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (39, 1, 'JOB', '391', 18.69875, 73.70526, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (39, 2, 'JOB', '67', 18.742105, 73.682827, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (39, 3, 'JOB', '121', 18.719882, 73.70536, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (39, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-07', 13.358, 0.376611, 8.3, 8.676611, '16:40', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (40, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (40, 1, 'JOB', '8', 18.731086, 73.664227, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (40, 2, 'JOB', '112', 18.715922, 73.68106, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (40, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-08', 13.5727, 0.402833, 8.4, 8.802833, '16:48', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (41, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (41, 1, 'JOB', '52', 18.750758, 73.670456, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (41, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-09', 8.5024, 0.277917, 8.6, 8.877917, '16:52', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (42, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (42, 1, 'JOB', '226', 18.718074, 73.700154, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (42, 2, 'JOB', '286', 18.730983, 73.681157, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (42, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-10', 5.7321, 0.224333, 8.5, 8.724333, '16:43', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (43, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (43, 1, 'JOB', '394', 18.734352, 73.679373, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (43, 2, 'JOB', '359', 18.735933, 73.680262, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (43, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-11', 18.9397, 0.548167, 8.4, 8.948167, '16:56', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (44, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (44, 1, 'JOB', '82', 18.721567, 73.689938, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (44, 2, 'JOB', '1', 18.749726, 73.672557, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (44, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-12', 19.576, 0.48575, 8.4, 8.88575, '16:53', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (45, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (45, 1, 'JOB', '103', 18.69804, 73.71191, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (45, 2, 'JOB', '13', 18.715468, 73.673796, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (45, 3, 'JOB', '16', 18.746606, 73.66876, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (45, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-13', 9.7751, 0.315333, 7.3, 7.615333, '15:36', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (46, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (46, 1, 'JOB', '208', 18.731241, 73.668021, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (46, 2, 'JOB', '412', 18.741344, 73.675277, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (46, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-14', 11.9358, 0.41325, 8.3, 8.71325, '16:42', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (47, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (47, 1, 'JOB', '281', 18.745878, 73.70717, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (47, 2, 'JOB', '43', 18.740751, 73.704556, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (47, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-15', 15.4433, 0.433222, 8.4, 8.833222, '16:49', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (48, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (48, 1, 'JOB', '367', 18.748322, 73.671046, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (48, 2, 'JOB', '113', 18.733837, 73.658787, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (48, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-16', 10.8926, 0.313222, 7.4, 7.713222, '15:42', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (49, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (49, 1, 'JOB', '215', 18.729498, 73.662473, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (49, 2, 'JOB', '256', 18.726434, 73.69621, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (49, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-17', 14.495, 0.523028, 7.5, 8.023028, '16:01', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (50, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (50, 1, 'JOB', '301', 18.708508, 73.702556, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (50, 2, 'JOB', '404', 18.741288, 73.688548, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (50, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-18', 6.051, 0.151444, 8.4, 8.551444, '16:33', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (51, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (51, 1, 'JOB', '170', 18.704813, 73.700158, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (51, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-19', 17.1769, 0.611611, 8.1, 8.711611, '16:42', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (52, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (52, 1, 'JOB', '4', 18.748642, 73.672136, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (52, 2, 'JOB', '334', 18.746384, 73.712423, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (52, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-20', 2.4356, 0.073639, 7.5, 7.573639, '15:34', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (53, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (53, 1, 'JOB', '19', 18.730033, 73.694688, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (53, 2, 'JOB', '97', 18.721081, 73.698849, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (53, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-21', 8.8861, 0.310556, 8.5, 8.810556, '16:48', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (54, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (54, 1, 'JOB', '28', 18.729427, 73.685417, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (54, 2, 'JOB', '364', 18.729996, 73.676315, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (54, 3, 'JOB', '151', 18.727982, 73.670873, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (54, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-22', 19.0173, 0.459333, 8.2, 8.659333, '16:39', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (55, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (55, 1, 'JOB', '196', 18.720818, 73.683247, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (55, 2, 'JOB', '499', 18.724799, 73.656751, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (55, 3, 'JOB', '421', 18.706768, 73.696391, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (55, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-23', 9.4309, 0.330528, 6.0, 6.330528, '14:19', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (56, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (56, 1, 'JOB', '37', 18.742114, 73.669606, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (56, 2, 'JOB', '241', 18.730844, 73.693364, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (56, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-24', 10.2425, 0.339111, 8.0, 8.339111, '16:20', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (57, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (57, 1, 'JOB', '250', 18.736781, 73.662012, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (57, 2, 'JOB', '439', 18.732258, 73.664756, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (57, 3, 'JOB', '229', 18.738814, 73.680792, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (57, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-25', 20.9615, 0.592667, 7.5, 8.092667, '16:05', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (58, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (58, 1, 'JOB', '88', 18.744653, 73.691076, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (58, 2, 'JOB', '469', 18.726855, 73.673776, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (58, 3, 'JOB', '172', 18.707498, 73.706445, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (58, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-26', 19.1185, 0.4955, 6.9, 7.3955, '15:23', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (59, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (59, 1, 'JOB', '427', 18.71252, 73.676949, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (59, 2, 'JOB', '337', 18.71866, 73.685016, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (59, 3, 'JOB', '73', 18.747654, 73.674417, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (59, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T002', '2026-10-27', 9.2753, 0.288972, 6.1, 6.388972, '14:23', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (60, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (60, 1, 'JOB', '91', 18.701306, 73.707743, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (60, 2, 'JOB', '160', 18.704378, 73.702643, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (60, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-09-28', 14.7811, 0.464639, 8.5, 8.964639, '16:57', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (61, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (61, 1, 'JOB', '493', 18.722209, 73.677948, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (61, 2, 'JOB', '415', 18.74163, 73.666994, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (61, 3, 'JOB', '373', 18.74662, 73.695154, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (61, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-09-29', 8.3596, 0.213167, 8.7, 8.913167, '16:54', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (62, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (62, 1, 'JOB', '329', 18.700035, 73.709393, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (62, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-09-30', 7.4459, 0.256306, 8.5, 8.756306, '16:45', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (63, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (63, 1, 'JOB', '500', 18.722888, 73.678967, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (63, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-01', 1.2684, 0.046667, 8.3, 8.346667, '16:20', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (64, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (64, 1, 'JOB', '443', 18.728582, 73.694201, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (64, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-02', 7.9578, 0.274389, 7.9, 8.174389, '16:10', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (65, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (65, 1, 'JOB', '236', 18.741675, 73.672457, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (65, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-03', 1.6518, 0.041444, 7.7, 7.741444, '15:44', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (66, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (66, 1, 'JOB', '38', 18.720523, 73.702453, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (66, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-04', 11.0335, 0.344056, 7.3, 7.644056, '15:38', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (67, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (67, 1, 'JOB', '442', 18.746457, 73.679857, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (67, 2, 'JOB', '403', 18.742421, 73.68188, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (67, 3, 'JOB', '184', 18.74649, 73.697192, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (67, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-05', 15.0659, 0.387, 7.9, 8.287, '16:17', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (68, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (68, 1, 'JOB', '448', 18.731375, 73.698715, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (68, 2, 'JOB', '22', 18.725876, 73.661001, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (68, 3, 'JOB', '127', 18.743504, 73.673102, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (68, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-06', 14.4164, 0.332444, 7.6, 7.932444, '15:55', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (69, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (69, 1, 'JOB', '494', 18.708553, 73.687381, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (69, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-07', 2.6392, 0.120333, 7.6, 7.720333, '15:43', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (70, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (70, 1, 'JOB', '419', 18.736471, 73.692288, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (70, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-08', 9.5714, 0.295528, 7.3, 7.595528, '15:35', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (71, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (71, 1, 'JOB', '287', 18.728417, 73.666146, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (71, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-09', 13.6229, 0.310417, 7.2, 7.510417, '15:30', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (72, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (72, 1, 'JOB', '290', 18.706988, 73.684374, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (72, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-10', 6.865, 0.253444, 7.1, 7.353444, '15:21', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (73, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (73, 1, 'JOB', '17', 18.730622, 73.673974, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (73, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-11', 12.3254, 0.409528, 6.9, 7.309528, '15:18', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (74, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (74, 1, 'JOB', '293', 18.717226, 73.706708, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (74, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-12', 13.6229, 0.310417, 6.7, 7.010417, '15:00', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (75, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (75, 1, 'JOB', '251', 18.709525, 73.685074, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (75, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-13', 14.589, 0.335611, 8.6, 8.935611, '16:56', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (76, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (76, 1, 'JOB', '382', 18.716846, 73.675062, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (76, 2, 'JOB', '44', 18.713756, 73.700597, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (76, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-14', 11.6786, 0.370056, 6.5, 6.870056, '14:52', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (77, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (77, 1, 'JOB', '227', 18.748683, 73.707113, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (77, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-15', 9.8212, 0.333056, 6.4, 6.733056, '14:43', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (78, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (78, 1, 'JOB', '41', 18.722704, 73.676147, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (78, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-16', 19.6615, 0.439889, 8.4, 8.839889, '16:50', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (79, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (79, 1, 'JOB', '190', 18.744117, 73.662879, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (79, 2, 'JOB', '98', 18.708487, 73.685071, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (79, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-17', 14.8715, 0.406806, 8.3, 8.706806, '16:42', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (80, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (80, 1, 'JOB', '397', 18.739109, 73.660935, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (80, 2, 'JOB', '71', 18.717434, 73.674057, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (80, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-18', 9.4432, 0.30525, 8.6, 8.90525, '16:54', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (81, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (81, 1, 'JOB', '428', 18.735408, 73.68261, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (81, 2, 'JOB', '94', 18.719464, 73.684095, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (81, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-19', 18.6116, 0.584194, 8.3, 8.884194, '16:53', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (82, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (82, 1, 'JOB', '193', 18.746234, 73.69017, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (82, 2, 'JOB', '449', 18.704926, 73.709685, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (82, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-20', 15.2715, 0.370861, 8.3, 8.670861, '16:40', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (83, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (83, 1, 'JOB', '265', 18.712066, 73.689862, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (83, 2, 'JOB', '488', 18.698117, 73.70688, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (83, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-21', 19.698, 0.553111, 7.8, 8.353111, '16:21', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (84, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (84, 1, 'JOB', '118', 18.730321, 73.662323, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (84, 2, 'JOB', '284', 18.715307, 73.703124, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (84, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-22', 15.3234, 0.413, 8.5, 8.913, '16:54', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (85, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (85, 1, 'JOB', '307', 18.736348, 73.693356, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (85, 2, 'JOB', '310', 18.722123, 73.67998, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (85, 3, 'JOB', '64', 18.709469, 73.687604, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (85, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T003', '2026-10-23', 17.057, 0.373278, 8.2, 8.573278, '16:34', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (86, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (86, 1, 'JOB', '247', 18.706055, 73.684373, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (86, 2, 'JOB', '175', 18.729975, 73.681613, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (86, 3, 'JOB', '325', 18.731379, 73.667031, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (86, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-09-28', 9.7947, 0.362222, 6.0, 6.362222, '14:21', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (87, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (87, 1, 'JOB', '405', 18.725679, 73.665978, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (87, 2, 'JOB', '372', 18.727393, 73.671716, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (87, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-09-29', 15.9823, 0.369639, 6.0, 6.369639, '14:22', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (88, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (88, 1, 'JOB', '369', 18.703875, 73.686178, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (88, 2, 'JOB', '459', 18.744583, 73.701988, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (88, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-09-30', 13.8561, 0.317694, 6.0, 6.317694, '14:19', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (89, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (89, 1, 'JOB', '249', 18.70274, 73.687168, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (89, 2, 'JOB', '222', 18.726155, 73.68087, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (89, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-01', 11.4261, 0.435056, 8.0, 8.435056, '16:26', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (90, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (90, 1, 'JOB', '340', 18.740607, 73.70795, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (90, 2, 'JOB', '174', 18.736972, 73.692528, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (90, 3, 'JOB', '327', 18.718977, 73.686839, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (90, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-02', 8.0814, 0.260611, 6.0, 6.260611, '14:15', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (91, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (91, 1, 'JOB', '153', 18.729701, 73.687241, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (91, 2, 'JOB', '354', 18.714105, 73.698803, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (91, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-03', 10.1869, 0.319111, 6.0, 6.319111, '14:19', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (92, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (92, 1, 'JOB', '351', 18.724198, 73.683838, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (92, 2, 'JOB', '57', 18.745649, 73.705383, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (92, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-04', 4.0876, 0.157833, 6.0, 6.157833, '14:09', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (93, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (93, 1, 'JOB', '204', 18.734159, 73.687754, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (93, 2, 'JOB', '45', 18.731316, 73.691424, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (93, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-05', 10.6737, 0.310306, 6.0, 6.310306, '14:18', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (94, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (94, 1, 'JOB', '360', 18.73392, 73.69266, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (94, 2, 'JOB', '150', 18.727616, 73.659288, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (94, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-06', 18.7869, 0.537361, 8.0, 8.537361, '16:32', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (95, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (95, 1, 'JOB', '225', 18.718337, 73.695514, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (95, 2, 'JOB', '210', 18.713191, 73.681763, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (95, 3, 'JOB', '100', 18.726333, 73.690204, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (95, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-07', 9.2905, 0.305444, 8.0, 8.305444, '16:18', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (96, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (96, 1, 'JOB', '322', 18.727957, 73.701211, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (96, 2, 'JOB', '451', 18.734726, 73.685209, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (96, 3, 'JOB', '49', 18.723195, 73.685861, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (96, 4, 'JOB', '230', 18.734157, 73.684496, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (96, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-08', 19.4981, 0.498222, 8.0, 8.498222, '16:29', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (97, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (97, 1, 'JOB', '163', 18.745395, 73.665148, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (97, 2, 'JOB', '272', 18.728087, 73.670817, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (97, 3, 'JOB', '491', 18.725741, 73.673252, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (97, 4, 'JOB', '263', 18.701697, 73.705392, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (97, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-09', 12.0382, 0.346333, 8.0, 8.346333, '16:20', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (98, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (98, 1, 'JOB', '157', 18.738144, 73.696596, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (98, 2, 'JOB', '470', 18.730163, 73.695836, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (98, 3, 'JOB', '344', 18.701708, 73.712805, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (98, 4, 'JOB', '89', 18.717372, 73.701057, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (98, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-10', 15.3672, 0.48775, 8.0, 8.48775, '16:29', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (99, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (99, 1, 'JOB', '125', 18.718928, 73.672103, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (99, 2, 'JOB', '353', 18.716327, 73.678227, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (99, 3, 'JOB', '352', 18.723832, 73.693954, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (99, 4, 'JOB', '430', 18.727081, 73.696026, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (99, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-11', 23.4679, 0.594083, 8.0, 8.594083, '16:35', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (100, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (100, 1, 'JOB', '79', 18.744545, 73.688021, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (100, 2, 'JOB', '199', 18.723263, 73.659227, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (100, 3, 'JOB', '244', 18.708585, 73.68739, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (100, 4, 'JOB', '85', 18.703483, 73.709369, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (100, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-12', 22.5603, 0.649167, 8.0, 8.649167, '16:38', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (101, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (101, 1, 'JOB', '400', 18.725549, 73.690924, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (101, 2, 'JOB', '223', 18.712209, 73.681723, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (101, 3, 'JOB', '178', 18.725609, 73.667414, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (101, 4, 'JOB', '95', 18.743573, 73.664486, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (101, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-13', 18.3837, 0.482306, 8.0, 8.482306, '16:28', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (102, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (102, 1, 'JOB', '5', 18.704151, 73.69439, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (102, 2, 'JOB', '380', 18.744442, 73.673521, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (102, 3, 'JOB', '475', 18.734937, 73.696882, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (102, 4, 'JOB', '197', 18.731887, 73.696693, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (102, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-14', 16.3145, 0.47225, 8.0, 8.47225, '16:28', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (103, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (103, 1, 'JOB', '271', 18.734983, 73.699937, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (103, 2, 'JOB', '454', 18.748389, 73.70387, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (103, 3, 'JOB', '119', 18.745212, 73.673748, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (103, 4, 'JOB', '268', 18.748185, 73.669326, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (103, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-15', 20.8092, 0.668222, 8.0, 8.668222, '16:40', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (104, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (104, 1, 'JOB', '128', 18.712464, 73.702348, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (104, 2, 'JOB', '182', 18.715622, 73.670721, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (104, 3, 'JOB', '166', 18.727709, 73.681532, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (104, 4, 'JOB', '140', 18.730445, 73.703703, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (104, 5, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-16', 15.4719, 0.572278, 6.0, 6.572278, '14:34', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (105, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (105, 1, 'JOB', '145', 18.732367, 73.685739, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (105, 2, 'JOB', '383', 18.714208, 73.695735, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (105, 3, 'JOB', '137', 18.713382, 73.704035, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (105, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-17', 12.894, 0.397639, 6.0, 6.397639, '14:23', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (106, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (106, 1, 'JOB', '297', 18.724406, 73.675647, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (106, 2, 'JOB', '267', 18.745516, 73.688506, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (106, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-18', 15.3084, 0.403028, 6.0, 6.403028, '14:24', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (107, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (107, 1, 'JOB', '48', 18.718887, 73.689196, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (107, 2, 'JOB', '246', 18.703119, 73.706955, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (107, 3, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-19', 11.7156, 0.367611, 8.0, 8.367611, '16:22', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (108, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (108, 1, 'JOB', '177', 18.712089, 73.70869, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (108, 2, 'JOB', '155', 18.70818, 73.712891, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (108, 3, 'JOB', '291', 18.717335, 73.698479, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (108, 4, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

INSERT INTO step13_routes (team_id, schedule_date, distance_km, travel_time_h, service_time_h, total_route_time_h, finish_time, status, source) VALUES ('T004', '2026-10-20', 12.5908, 0.425944, 3.0, 3.425944, '11:25', 'PASS', 'final_step13_route_audit');
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (109, 0, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (109, 1, 'JOB', '81', 18.714306, 73.711784, NULL, NULL);
INSERT INTO step13_route_stops (route_id, stop_order, node_type, job_id, latitude, longitude, travel_distance_m, travel_time_s) VALUES (109, 2, 'DEPOT', NULL, 18.729411, 73.699489, NULL, NULL);

COMMIT;

-- ================================================================
-- VERIFICATION
-- ================================================================

SELECT COUNT(*) AS route_count FROM step13_routes;

SELECT COUNT(*) AS route_stop_count FROM step13_route_stops;

SELECT COUNT(DISTINCT job_id) AS unique_route_jobs FROM step13_route_stops WHERE node_type = 'JOB';

SELECT status, COUNT(*) AS route_count FROM step13_routes GROUP BY status ORDER BY status;

SELECT team_id, COUNT(*) AS route_count, SUM(distance_km) AS distance_km, SUM(total_route_time_h) AS route_hours FROM step13_routes GROUP BY team_id ORDER BY team_id;

SELECT MIN(finish_time) AS earliest_finish, MAX(finish_time) AS latest_finish FROM step13_routes;