# Title     : Individual data description
# Objective : Histogram
# Created by: Yuan Liao
# Created on: 2023-4-29

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
options(scipen=10000)

#------------ Experienced segregion --------------
# Load all features
feature_dict <- list(weekend='Weekend', weekday='Weekday',
                     non_holiday='Non-holiday', holiday='Holiday',
                     number_of_locations='No. of unique locations visited',
                     number_of_visits='No. of visits',
                     average_displacement='Average displacement',
                     radius_of_gyration='Radius of gyration',
                     median_distance_from_home='Median distance from home',
                     `Not Sweden`='Prob. born outside Sweden',
                     `Lowest income group`='Prob. in lowest income group',
                     car_ownership='Prob. of owning a car',
                     cum_jobs='Job accessibility by car',
                     cum_stops='Transit accessibility by walking',
                     evenness_income_resi='Residential income segregation',
                     evenness_income='Experienced income segregation',
                     num_jobs='Job density at residence',
                     num_stops='Transit stop density at residence',
                     gsi='GSI at residence',
                     length_density='Pedestrian network density at residence')

df.vis <- as.data.frame(read_parquet('results/data4model_individual.parquet'))

fb.tre.low <- 0.4
fb.tre.high <- 0.1
df.vis$income_gp <- NA
df.vis$income_gp[df.vis$`Lowest income group` > fb.tre.low] <- "Low income"
df.vis$income_gp[df.vis$`Lowest income group` <= fb.tre.high] <- "High income"
df.vis <- na.omit(df.vis)

# Overall data
df <- as.data.frame(read_parquet('results/data4model_individual.parquet'))

distribution.plot <- function(var, bin_num, log.label) {
  x.label <- feature_dict[var]
  g <- ggplot() +
  scale_color_manual(name='Income group',
                 breaks=c('High income', 'Low income', 'All'),
                 values=c('High income'='steelblue', 'Low income'='orange', 'All'='white')) +
  geom_histogram(data=df, aes(x=.data[[var]], color = 'All'), fill='gray', bins=bin_num, alpha=0.3) +
  stat_bin(data=df.vis, aes(x=.data[[var]], color = .data[['income_gp']]), geom="step", bins=bin_num) +
  labs(y = 'Frequency', x = x.label) +
  theme_minimal() +
  theme(legend.position="top")
  if (log.label == TRUE) {
    x.lower <- log10(max(min(df[,var]), 0.01))
    x.upper <- log10(max(df[,var]))
    br <- (x.upper - x.lower) / bin_num
    g <- ggplot() +
      scale_color_manual(name='Income group',
                     breaks=c('High income', 'Low income', 'All'),
                     values=c('High income'='steelblue', 'Low income'='orange', 'All'='white')) +
      geom_histogram(data=df, aes(x=.data[[var]], color = 'All'), fill='gray',
                     breaks=10^seq(x.lower, x.upper, br), alpha=0.3) +
      stat_bin(data=df.vis, aes(x=.data[[var]], color = .data[['income_gp']]), geom="step",
               breaks=10^seq(x.lower, x.upper, br)) +
      labs(y = 'Frequency', x = x.label) +
      theme_minimal() +
      theme(legend.position="top") +
      scale_x_log10(breaks = trans_breaks("log10", function(x) 10^x),
                    labels = trans_format("log10", math_format(10^.x)))
  }
  return(g)
}

g0 <- distribution.plot(var='evenness_income', bin_num=50, log.label=T)
g1 <- distribution.plot(var='evenness_income_resi', bin_num=50, log.label=F)

# Mobility characteristics
g2 <- distribution.plot(var='number_of_locations', bin_num=50, log.label=T)
g3 <- distribution.plot(var='number_of_visits', bin_num=50, log.label=T)
g4 <- distribution.plot(var='average_displacement', bin_num=50, log.label=T)
g5 <- distribution.plot(var='radius_of_gyration', bin_num=50, log.label=T)

# Individual attributes
g7 <- distribution.plot(var='Not Sweden', bin_num=50, log.label=F)
g8 <- distribution.plot(var='Lowest income group', bin_num=50, log.label=F)
g9 <- distribution.plot(var='car_ownership', bin_num=50, log.label=F)

g12 <- distribution.plot(var='num_jobs', bin_num=50, log.label=T)
g14 <- distribution.plot(var='length_density', bin_num=50, log.label=T)

# Zero treatment needed
g10 <- distribution.plot(var='cum_jobs', bin_num=50, log.label=T)
g11 <- distribution.plot(var='cum_stops', bin_num=50, log.label=T)
g6 <- distribution.plot(var='median_distance_from_home', bin_num=50, log.label=T)
g13 <- distribution.plot(var='num_stops', bin_num=50, log.label=F)



