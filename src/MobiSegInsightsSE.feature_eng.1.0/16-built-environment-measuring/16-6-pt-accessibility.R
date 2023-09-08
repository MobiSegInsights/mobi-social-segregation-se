# Title     : Accessibility to jobs by public transit
# Objective : Calculate PT access to jobs by county
# Created by: Yuan Liao
# Created on: 2023-09-07

options(java.parameters = "-Xmx48G")

library(r5r)
library(sf)
library(data.table)
library(ggplot2)
library(interp)
library(dplyr)

# system.file returns the directory with example data inside the r5r package
# set data path to directory containing your own data if not using the examples
tp_path <- "dbs/accessibility" # system.file("extdata/poa", package = "r5r")
counties <- c('14', '17', '18', '19', '20',
              '21', '22', '23', '24', '25')
counties.done <- c('01', '03', '04', '05', '06', '07', '08', '09', '10', '12', '13')

ct.process <- function(county){
  output_path <- paste0(tp_path, "/results/access_", county, ".csv")
  data_path <- paste0(tp_path, "/c_", county)
  # Indicate the path where OSM and GTFS data are stored
  r5r_core <- setup_r5(data_path = data_path)
  origins <- fread(file.path(paste0(tp_path, '/data'), paste0("origins_", county, ".csv")))
  destinations <- fread(file.path(paste0(tp_path, '/data'), paste0("destinations_", county, ".csv")))
  # set departure datetime input
  departure_datetime <- as.POSIXct("07-09-2023 14:00:00",
                                   format = "%d-%m-%Y %H:%M:%S")
  # calculate accessibility
  access <- accessibility(r5r_core = r5r_core,
                          origins = origins,
                          destinations = destinations,
                          opportunities_colnames = "job",
                          mode = c("WALK", "TRANSIT"),
                          departure_datetime = departure_datetime,
                          decay_function = "step",
                          cutoffs = 30,
                          verbose = FALSE,
                          progress = TRUE)
  write.csv(access, file = output_path, row.names = FALSE)
}

for (county in counties){
  print(paste("Processing county:", county))
  ct.process(county = county)
}

