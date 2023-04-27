# Title     : Feature interaction effect
# Objective : Feature interaction effect
# Created by: Yuan Liao
# Created on: 2020-11-29

library(stringr)
library(dplyr)
library(ggplot2)
library(ggpubr)
library(yaml)
library(DBI)
library(RPostgres)
library(scico)

fake_scico <- scico(3, palette = "vik")
every_n_labeler <- function(n = 2) {
  function (x) {
    ind <- ((seq_along(x)) - 1) %% n == 0
    x[!ind] <- ""
    return(x)
  }
}

feature_dict <- list(tt_transit_ob="TT ratio excl. access/egress walking",
                     tt_car="TT by ride-sourcing, min",
                     pickup_zone_cluster="Functional cluster (pick-up zone)",
                     dropoff_zone_cluster="Functional cluster (drop-off zone)",
                     pickup_zone_comm="Demand community (pick-up zone)",
                     dropoff_zone_comm="Demand community (drop-off zone)",
                     pickup_zone_transit_density="Transit stop density \n (pick-up zone),",
                     dropoff_zone_transit_density="Transit stop density \n (drop-off zone),",
                     num_boardings="# of boardings",
                     weather_coded="Weather")
# as.expression(bquote("# of requests "(10^3)))
# List all the interactions
path <- 'results/interactions'
inters <- c('tt_transit_ob x num_boardings', 'pickup_zone_comm x tt_transit_ob',
            'weather_coded x tt_transit_ob', 'num_boardings x dropoff_zone_cluster',
            'dropoff_zone_transit_density x dropoff_zone_cluster', 'dropoff_zone_comm x dropoff_zone_cluster',
            'dropoff_zone_comm x pickup_zone_comm', 'pickup_zone_cluster x dropoff_zone_cluster')

labels_cat <- c('pickup_zone_cluster', 'dropoff_zone_cluster','weather_coded',
                'pickup_zone_comm', 'dropoff_zone_comm', 'num_boardings')

cate2factor <- function(var_name, df2plot){
  if(var_name == 'weather_coded'){
    df2plot[, var_name] <- factor(df2plot[, var_name], levels=c('Clear', 'Clouds', 'Haze', 'Fog', 'Mist', 'Rain'),
                        labels=c('Clear', 'Clouds', 'Haze', 'Fog', 'Mist', 'Rain'))
  }
  if(var_name %in% c('pickup_zone_comm', 'dropoff_zone_comm')){
    df2plot[, var_name] <- factor(df2plot[, var_name], levels=c('North', 'South-west', 'South-east'),
                        labels=c('North', 'South-West', 'South-East'))
  }
  if(var_name %in% c('pickup_zone_cluster', 'dropoff_zone_cluster')){
    df2plot[, var_name] <- factor(df2plot[, var_name], levels=c('Centre', 'Centre-business', 'Transition',
'Residential-business', 'Outer-residential', 'Business-residential', 'Rural'),
                        labels=c('Centre', 'Centre-business', 'Transition',
'Residential-business', 'Outer-residential', 'Business-residential', 'Rural'))
  }
  if(var_name == 'num_boardings'){
    df2plot[, var_name] <- factor(df2plot[, var_name])
  }
  return(df2plot)
}
# Test on one interaction matrix
test_id <- 2

inter2plot <- function(test_id, flip, x_angle, y_angle){
  df2plot <- read.csv(paste0(path, '/', inters[test_id], '.csv'))
  df2plot <- df2plot[df2plot$freq > 5,]
  var1 <- unlist(str_split(inters[test_id], " x "))[1]
  var2 <- unlist(str_split(inters[test_id], " x "))[2]
  if(var1 %in% labels_cat){df2plot <- cate2factor(var1, df2plot)}else{df2plot[,var1] <- factor(round(df2plot[,var1], digits = 1))}
  if(var2 %in% labels_cat){df2plot <- cate2factor(var2, df2plot)}else{df2plot[,var2] <- factor(round(df2plot[,var2], digits = 1))}

  if((var1 %in% labels_cat) & (var2 %in% labels_cat)){
    g1 <- ggplot(df2plot, aes_string(x=var1, y=var2)) +
    geom_tile(aes(fill = f), colour = NA) +
    scale_fill_gradient2(name='Score', low = fake_scico[1], mid = fake_scico[2], high = fake_scico[3]) +
    theme_minimal() +
    labs(x=feature_dict[var1], y=feature_dict[var2]) +
    theme(legend.position = "top", legend.key.width = unit(1, "cm"),
          panel.grid = element_blank(),
          axis.text.x = element_text(angle = x_angle, vjust=0.7), axis.text.y = element_text(angle = y_angle, vjust=0.7))
  }
  # Plot the matrix
  if((var1 %in% labels_cat) & !(var2 %in% labels_cat)){
    g1 <- ggplot(df2plot, aes_string(x=var1, y=var2)) +
    geom_tile(aes(fill = f), colour = NA) +
    scale_fill_gradient2(name='Score', low = fake_scico[1], mid = fake_scico[2], high = fake_scico[3]) +
    theme_minimal() +
    scale_y_discrete(labels = every_n_labeler(3)) +
    labs(x=feature_dict[var1], y=feature_dict[var2]) +
    theme(legend.position = "top", legend.key.width = unit(1, "cm"),
          panel.grid = element_blank(),
          axis.text.x = element_text(angle = x_angle, vjust=0.7), axis.text.y = element_text(angle = y_angle, vjust=0.7))
  }

  if(!(var1 %in% labels_cat) & (var2 %in% labels_cat)){
    g1 <- ggplot(df2plot, aes_string(x=var1, y=var2)) +
      geom_tile(aes(fill = f), colour = NA) +
      scale_fill_gradient2(name='Score', low = fake_scico[1], mid = fake_scico[2], high = fake_scico[3]) +
      theme_minimal() +
      scale_x_discrete(labels = every_n_labeler(3)) +
      labs(x=feature_dict[var1], y=feature_dict[var2]) +
      theme(legend.position = "top", legend.key.width = unit(1, "cm"),
            panel.grid = element_blank(),
          axis.text.x = element_text(angle = x_angle, vjust=0.7), axis.text.y = element_text(angle = y_angle, vjust=0.7))
  }

  if(!(var1 %in% labels_cat) & !(var2 %in% labels_cat)){
    g1 <- ggplot(df2plot, aes_string(x=var1, y=var2)) +
      geom_tile(aes(fill = f), colour = NA) +
      scale_fill_gradient2(name='Score', low = fake_scico[1], mid = fake_scico[2], high = fake_scico[3]) +
      theme_minimal() +
      scale_x_discrete(labels = every_n_labeler(3)) +
      scale_y_discrete(labels = every_n_labeler(3)) +
      theme(legend.position = "top", legend.key.width = unit(1, "cm"),
            panel.grid = element_blank(),
          axis.text.x = element_text(angle = x_angle, vjust=0.7), axis.text.y = element_text(angle = y_angle, vjust=0.7))
  }
  if(var1 == 'dropoff_zone_transit_density'){
    g1 <- g1 + labs(x=bquote("Transit stop density (drop-off zone),"~1/km^2), y=feature_dict[var2])
  } else
  {
    g1 <- g1 + labs(x=feature_dict[var1], y=feature_dict[var2])
  }
  if(flip==1){g1 <- g1 + coord_flip()}
  return(g1)
}

g1 <- inter2plot(1, 1,0, 0)
g2 <- inter2plot(2, 0, 0,0)
g3 <- inter2plot(3, 0, 0,0)
g4 <- inter2plot(4, 1, 30, 0)
g5 <- inter2plot(5, 1, 30, 0)
g6 <- inter2plot(6, 1, 30, 0)
g7 <- inter2plot(7, 1, 0,0)
g8 <- inter2plot(8, 0, 30, 30)

# Save figure
G1 <- ggarrange(g1, g2, g3, g4,
               labels = c('(A)', '(B)', '(C)', '(D)'), ncol = 4, nrow = 1)
G2 <- ggarrange(g5, g6, g7, g8,
               labels = c('(E)', '(F)', '(G)', '(H)'), ncol = 4, nrow = 1)
G <- ggarrange(G1, G2, ncol = 1, nrow = 2)
h <- 8
ggsave(filename = "./figures/interaction_heatmap_masked.png", plot=G,
       width = h / 2 * 4, height = h, unit = "in", dpi = 300)