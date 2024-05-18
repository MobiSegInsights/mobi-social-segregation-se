# Title     : Probability distribution of distance to home
# Objective : All, F, and D
# Created by: Yuan Liao
# Created on: 2023-12-11

library(dplyr)
library(tidyr)
library(ggplot2)
library(ggthemes)
library(rjson)
library(glue)
library(ggpubr)
library(latex2exp)
library(scales)
options(scipen=10000)

df <- read.csv('results/distance_decay_DFA.csv')
df$Type <- recode(df$Type, `D` = "N")

df.s <- filter(df, `d` %in% c(1, 3, 10, 32, 100, 316, 1000, 1500))

df <- df %>%
  filter(Type == 'All')
cols <- c("#601200", "#001260", "#485460")
g1 <- ggplot() +
    geom_point(data = df.s, aes(y=fd, x=as.numeric(d), color=Type, shape=Type), size=1, alpha=1) +
    geom_line(data = df.s, aes(y=fd, x=as.numeric(d), color=Type), alpha=0.5, size=0.5) +
    scale_color_manual(name='Type',
                       breaks=c('All', 'F', 'N'),
                       values=c('All'=cols[3],
                                'N'=cols[2],
                                'F'=cols[1])) +
  scale_shape_manual(name='Type',
                       breaks=c('All', 'F', 'N'),
                       values=c('All'=19,
                                'N'=1,
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
h <- 4
w <- 6
ggsave(filename = glue("figures/limited_travel_dist.png"), plot=g1,
       width = w, height = h, unit = "in", dpi = 300)

# ------ Pole axis for illustration -----
df_expanded <- read.csv('results/distance_decay_DFA.csv') %>%
  mutate(Type = recode(Type, `D` = "N")) %>%
  group_by(Type, d) %>%
  expand(angle = seq(0, 2*pi, length.out = 10)) %>%
  ungroup()

df <- read.csv('results/distance_decay_DFA.csv') %>%
  mutate(Type = recode(Type, `D` = "N")) %>%
  select(Type, d, fd)

df_expanded <- merge(df_expanded, df, on=c('Type', 'd'), how='left')

g2 <- ggplot(df_expanded, aes(x=angle, y = d, fill = fd)) +
  theme_hc() +
  geom_tile() +
  scale_fill_viridis_c(name='Probability',
                       breaks = c(0.0000001, 0.3),
                       labels = c("10^-7", "0.3"),
                       trans = "log") +  # Customize color gradient as needed
  coord_polar() +
  facet_grid(.~Type) +
  labs(title = "Visit probability", x = "Travel direction", y = "Distance (km)") +
  theme(axis.title.x=element_blank(),
        axis.text.x=element_blank(),
        axis.ticks.x=element_blank(),
        strip.background = element_blank(),
        legend.position = 'top')

ggsave(filename = glue("figures/limited_travel_dist_d.png"), plot=g2,
       width = 12, height = 4, unit = "in", dpi = 300)