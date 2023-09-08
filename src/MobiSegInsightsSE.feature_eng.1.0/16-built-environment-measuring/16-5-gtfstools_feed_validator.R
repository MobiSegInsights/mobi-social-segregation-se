# Title     : GTFS data fixing
# Objective : Examine GTFS data for the entire Sweden and fix errors
# Created by: Rafael H. M. Pereira
# Revised by: Yuan Liao
# Created on: 2023-09-06

options(java.parameters = '-Xmx32G')

library(gtfstools)
library(data.table)

gtfs.data.path <- '../../../dbs/gtfs_sweden_2023-09-06/sweden.zip'
gtfs.data.fixed.path <- '../../../dbs/accessibility/sweden_fixed.zip'

## onlye n
gtfstools::download_validator(path = '../../../tests')

gtfstools::validate_gtfs(gtfs = gtfs.data.path,
                         validator_path = 'gtfs-validator-v4.0.0.jar', 
                         output_path = 'report')


df <- gtfstools::read_gtfs(gtfs.data.path)

# point_near_origin: some stops have spatial coordinates with value 0
nrow(df$stops[stop_lat ==0] )
#> 49

# Replace route_type 1501 with 3
df$routes[route_type == 1501,]$route_type <- 3

# determine ids of problematic stops
stop_ids_error <- df$stops[stop_lat ==0 | stop_lon ==0,]$stop_id

# remove problematic stops and their corresponding trips
df <- gtfstools::filter_by_stop_id(gtfs = df, stop_id = stop_ids_error, keep = F)

# drop shape_dist_traveled column
df$stop_times[, shape_dist_traveled := NULL]

# remove invalid transfer
df$transfers <- df$transfers[!(to_trip_id=='747400000000001187' & to_stop_id == '9022050000133008')]

# drop attributions.txt table (optional)
df$attributions <- NULL

# drop shapes.txt table (optional)
df$shapes <- NULL

# remove table not used
df$feed_info <- NULL

gtfstools::write_gtfs(df, gtfs.data.fixed.path)
