# An input variable named "namespaces"; main.tf reads it as var.namespaces
variable "namespaces" {
  # Human-readable explanation of what it is for
  description = "Namespaces to create in the cluster"
  # The value must be a list of text values
  type = list(string)
  # Used when nobody provides a value; change this list to add or remove namespaces
  default = ["ci", "mlops", "training", "serving", "monitoring"]
}
