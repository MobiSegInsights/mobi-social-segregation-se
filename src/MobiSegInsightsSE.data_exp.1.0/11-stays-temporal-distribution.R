# Title     : Temporal distribution of stays
# Objective : In contrast with travel survey
# Created by: Yuan Liao
# Created on: 2023-04-05

library(dplyr)
library(ggplot2)
library(ggsci)
library(ggpubr)
library(ggspatial)
library(sf)
library(ggraph)
library(scico)
library(yaml)
library(DBI)
library(scales)
options(scipen=10000)

# Load temporal profile of MAD
df.tempo <- read.csv('results/activity_patterns_mad.csv')
df.tempo$activity <- plyr::mapvalues(df.tempo$activity,
                                        from=c('all', 'holiday', 'non_holiday'),
                                        to=c("Total","Holiday","Non-holiday"))
g1 <- ggplot(data = df.tempo) +
  geom_line(aes(x = half_hour / 2, y = freq/1000000,
                group = activity, color = activity)) +
  scale_color_discrete(name = 'Type') +
  labs(x = 'Hour of day', y = 'Number of stays (million)') +
  scale_y_continuous() +
  theme_minimal() +
  theme(plot.margin = margin(1,1,0,0, "cm"),
        legend.position = 'top')

ggsave(filename = "figures/stays_tempo_mad.png", plot=g1,
       width = 7, height = 4, unit = "in", dpi = 300)

# Load temporal profile of MAD
df.tempo.sv <- read.csv('../../results/activity_patterns_survey.csv')
g2 <- ggplot(data = df.tempo.sv) +
  geom_line(aes(x = half_hour / 2, y = freq,
                group = activity, color = activity)) +
  scale_color_discrete(name = 'Type') +
  labs(x = 'Hour of day', y = 'Number of stays') +
  scale_y_continuous() +
  theme_minimal() +
  theme(plot.margin = margin(1,1,0,0, "cm"),
        legend.position = 'top')

G <- ggarrange(g1, g2, ncol = 2, nrow = 1,
               labels = c('(a) Mobile application data', '(b) Travel survey'))
ggsave(filename = paste0("../../figures/stays_tempo_vs_survey.png"), plot=G,
       width = 8, height = 4, unit = "in", dpi = 300)