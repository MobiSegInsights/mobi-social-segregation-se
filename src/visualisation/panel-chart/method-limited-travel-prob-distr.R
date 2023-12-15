# Title     : Probability distribution of distance to home
# Objective : All, F, and D
# Created by: Yuan Liao
# Created on: 2023-12-11

library(dplyr)
library(ggplot2)
library(rjson)
library(glue)
library(ggpubr)
library(latex2exp)
library(scales)
options(scipen=10000)

df <- read.csv('results/distance_decay_DFA.csv')
df.s <- df %>%
  filter(d %in% c(1, 3, 10, 32, 100, 316, 1000, 1500))
df <- df %>%
  filter(Type == 'All')
cols <- c("#601200", "#001260", "#485460")
g1 <- ggplot() +
    geom_point(data = df.s, aes(y=fd, x=as.numeric(d), color=Type, shape=Type), size=1, alpha=1) +
    geom_line(data = df.s, aes(y=fd, x=as.numeric(d), color=Type), alpha=0.5, size=0.5) +
    scale_color_manual(name='Type',
                       breaks=c('All', 'F', 'D'),
                       values=c('All'=cols[3],
                                'D'=cols[2],
                                'F'=cols[1])) +
  scale_shape_manual(name='Type',
                       breaks=c('All', 'F', 'D'),
                       values=c('All'=19,
                                'D'=1,
                                'F'=3)) +
    scale_y_log10(limits = c(0.000001, 1),
                  breaks = trans_breaks("log10", function(x) 10^x),
                  labels = trans_format("log10", scales::math_format(10^.x))) +
    scale_x_log10(limits = c(min(df[, 'd']), max(df[, 'd'])),
                  breaks = trans_breaks("log10", function(x) 10^x),
                  labels = trans_format("log10", scales::math_format(10^.x))) +
    theme_classic() +
    theme(
      plot.title = element_text(size=9),
      legend.position = c(0.3, 0.2),
      panel.border = element_blank(),
    ) +
    xlab("Distance (km)") +
    ylab("Trip frequency rate") +
    geom_point(data = df, aes(y=fd, x=as.numeric(d)), size=0.1, alpha=0.2) +
    theme(plot.margin = margin(1,0.5,0,0, "cm"))
g1


# save plot
h <- 5
w <- 5
ggsave(filename = glue("figures/limited_travel_dist.png"), plot=g1,
       width = w, height = h, unit = "in", dpi = 300)

