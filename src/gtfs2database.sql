-- The below code is adapted from https://docs.mobilitydb.com/MobilityDB-workshop/master/ch04.html
CREATE TABLE gtfs.agency (
  agency_id text DEFAULT '',
  agency_name text DEFAULT NULL,
  agency_url text DEFAULT NULL,
  agency_timezone text DEFAULT NULL,
  agency_lang text DEFAULT NULL,
  agency_phone text DEFAULT NULL,
  CONSTRAINT agency_pkey PRIMARY KEY (agency_id)
);

CREATE TABLE gtfs.calendar (
  service_id text,
  monday int NOT NULL,
  tuesday int NOT NULL,
  wednesday int NOT NULL,
  thursday int NOT NULL,
  friday int NOT NULL,
  saturday int NOT NULL,
  sunday int NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  CONSTRAINT calendar_pkey PRIMARY KEY (service_id)
);

CREATE INDEX calendar_service_id ON gtfs.calendar (service_id);

CREATE TABLE gtfs.exception_types (
  exception_type int PRIMARY KEY,
  description text
);

CREATE TABLE gtfs.calendar_dates (
  service_id text,
  date date NOT NULL,
  exception_type int REFERENCES gtfs.exception_types(exception_type)
);
CREATE INDEX calendar_dates_dateidx ON gtfs.calendar_dates (date);

CREATE TABLE gtfs.routes (
  route_id text,
  agency_id text,
  route_short_name text DEFAULT '',
  route_long_name text DEFAULT '',
  route_type int,
  route_desc text DEFAULT '',
  CONSTRAINT routes_pkey PRIMARY KEY (route_id)
);
-- gtfs.shapes table is created using python pandas outside this script to clean up data and dump to the database
-- CREATE TABLE gtfs.shapes (
--   shape_id text NOT NULL,
--   shape_pt_lat double precision NOT NULL,
--   shape_pt_lon double precision NOT NULL,
--   shape_pt_sequence int NOT NULL
-- );
CREATE INDEX shapes_shape_key ON gtfs.shapes (shape_id);

-- Create a table to store the shape geometries
CREATE TABLE gtfs.shape_geoms (
  shape_id text NOT NULL,
  shape_geom geometry('LINESTRING', 4326),
  CONSTRAINT shape_geom_pkey PRIMARY KEY (shape_id)
);
CREATE INDEX shape_geoms_key ON gtfs.shapes (shape_id);

CREATE TABLE gtfs.location_types (
  location_type int PRIMARY KEY,
  description text
);

CREATE TABLE gtfs.stops (
  stop_id text,
  stop_name text DEFAULT NULL,
  stop_lat double precision,
  stop_lon double precision,
  location_type integer  REFERENCES gtfs.location_types(location_type),
  parent_station integer,
  stop_geom geometry('POINT', 4326),
  platform_code text DEFAULT NULL,
  CONSTRAINT stops_pkey PRIMARY KEY (stop_id)
);
CREATE TABLE gtfs.pickup_dropoff_types (
  type_id int PRIMARY KEY,
  description text
);

CREATE TABLE gtfs.stop_times (
  trip_id text NOT NULL,
  -- Check that casting to time interval works.
  arrival_time interval CHECK (arrival_time::interval = arrival_time::interval),
  departure_time interval CHECK (departure_time::interval = departure_time::interval),
  stop_id text,
  stop_headsign text,
  stop_sequence int NOT NULL,
  pickup_type int REFERENCES gtfs.pickup_dropoff_types(type_id),
  drop_off_type int REFERENCES gtfs.pickup_dropoff_types(type_id),
  shape_dist_traveled double precision,
  timepoint double precision,
  CONSTRAINT stop_times_pkey PRIMARY KEY (trip_id, stop_sequence)
);
CREATE INDEX stop_times_key ON gtfs.stop_times (trip_id, stop_id);
CREATE INDEX arr_time_index ON gtfs.stop_times (arrival_time);
CREATE INDEX dep_time_index ON gtfs.stop_times (departure_time);

CREATE TABLE gtfs.trips (
  route_id text NOT NULL,
  service_id text NOT NULL,
  trip_id text NOT NULL,
  trip_headsign text,
  direction_id int,
  shape_id text,
  CONSTRAINT trips_pkey PRIMARY KEY (trip_id)
);
CREATE INDEX trips_trip_id ON gtfs.trips (trip_id);

INSERT INTO gtfs.exception_types (exception_type, description) VALUES
(1, 'service has been added'),
(2, 'service has been removed');

INSERT INTO gtfs.location_types(location_type, description) VALUES
(0,'stop'),
(1,'station'),
(2,'station entrance');

INSERT INTO gtfs.pickup_dropoff_types (type_id, description) VALUES
(0,'Regularly Scheduled'),
(1,'Not available'),
(2,'Phone arrangement only'),
(3,'Driver arrangement only');

COPY gtfs.calendar(service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,
                   start_date,end_date)
    FROM 'D:/mobi-social-segregation-se/dbs/gtfs_sweden_2023-02-06/sweden/calendar.txt'
    DELIMITER ',' CSV HEADER;

COPY gtfs.calendar_dates(service_id,date,exception_type)
    FROM 'D:/mobi-social-segregation-se/dbs/gtfs_sweden_2023-02-06/sweden/calendar_dates.txt'
    DELIMITER ',' CSV HEADER;

COPY gtfs.stop_times(trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,
                     pickup_type,drop_off_type,shape_dist_traveled,timepoint)
    FROM 'D:/mobi-social-segregation-se/dbs/gtfs_sweden_2023-02-06/sweden/stop_times.txt'
    DELIMITER ',' CSV HEADER;

COPY gtfs.trips(route_id,service_id,trip_id,trip_headsign,direction_id,shape_id)
    FROM 'D:/mobi-social-segregation-se/dbs/gtfs_sweden_2023-02-06/sweden/trips.txt'
    DELIMITER ',' CSV HEADER;

COPY gtfs.agency(agency_id,agency_name,agency_url,agency_timezone,agency_lang,agency_phone)
    FROM 'D:/mobi-social-segregation-se/dbs/gtfs_sweden_2023-02-06/sweden/agency.txt'
    DELIMITER ',' CSV HEADER;

COPY gtfs.routes(route_id,agency_id,route_short_name,route_long_name,route_type,route_desc)
    FROM 'D:/mobi-social-segregation-se/dbs/gtfs_sweden_2023-02-06/sweden/routes.txt'
    DELIMITER ',' CSV HEADER;

COPY gtfs.stops(stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station,platform_code)
    FROM 'D:/mobi-social-segregation-se/dbs/gtfs_sweden_2023-02-06/sweden/stops.txt'
    DELIMITER ',' CSV HEADER;

INSERT INTO gtfs.shape_geoms
SELECT shape_id, ST_MakeLine(array_agg(
  ST_SetSRID(ST_MakePoint(shape_pt_lon, shape_pt_lat),4326) ORDER BY shape_pt_sequence))
FROM gtfs.shapes
GROUP BY shape_id;

UPDATE gtfs.stops
SET stop_geom = ST_SetSRID(ST_MakePoint(stop_lon, stop_lat),4326)
WHERE stop_lon > 0;
